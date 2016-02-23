from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals

from dulwich.diff_tree import _tree_entries, _NULL_ENTRY, TreeEntry, _is_tree
from gittle import Gittle
from dulwich import porcelain
import stat
from git import diff3
from git.gitutils import _get_repo, find_revision_sha, can_ff, merge_base, count_commits_between, is_ancestor, get_remote_tracking_branch, GitError
import argparse
from six.moves import zip
from io import open as io_open



def _merge_entries(path, trees):
    """Merge the entries of two trees.

    :param path: A path to prepend to all tree entry names.
    :param tree1: The first Tree object to iterate, or None.
    :param tree2: The second Tree object to iterate, or None.
    :return: A list of pairs of TreeEntry objects for each pair of entries in
        the trees. If an entry exists in one tree but not the other, the other
        entry will have all attributes set to None. If neither entry's path is
        None, they are guaranteed to match.
    """
    entries=[]
    for tree in trees:
        entries.append(_tree_entries(path, tree))
    
    inds=[]
    lens=[]
    for e in entries:
        inds.append(0)
        lens.append(len(e))

    result = []
    while any([ind < l for ind,l in zip(inds,lens)]):
        next_entry=[e[ind] if ind<l else _NULL_ENTRY for e,ind,l in zip(entries,inds,lens)]
        paths=[e.path  for e in next_entry if e.path]
        minpath=min(paths)
        merged=[e if e.path == minpath else _NULL_ENTRY for e in next_entry]
        result.append(merged)
        inds=[ind+1 if e.path == minpath else ind for e,ind in zip(next_entry,inds)]
        
    return result
    
def all_eq(entries):
    all([i==j for i in entries for j in entries])
    
def first_nonempty(entries):
    result=None
    for entry in entries:
        result=result or entry
    return result
    
def walk_trees(store, tree_ids,prune_identical=False):
    """Recursively walk all the entries of N trees.

    Iteration is depth-first pre-order, as in e.g. os.walk.

    :param store: An ObjectStore for looking up objects.
    :param trees: iterable of SHAs for N trees
    :param prune_identical: If True, identical subtrees will not be walked.
    :return: Iterator over tuple contsining N TreeEntry objects for each of entries
        in the trees and their subtrees recursively. If an entry exists in one
        tree but not the other, the other entry will have all attributes set
        to None. If neither entry's path is None, they are guaranteed to
        match.
    """
    # This could be fairly easily generalized to >2 trees if we find a use
    # case.
    modes= [tree_id and stat.S_IFDIR or None for tree_id in tree_ids]
    todo = [[TreeEntry(b'', mode, tree_id) for mode,tree_id in zip(modes,tree_ids)]]

    while todo:
        entries = todo.pop()
        is_trees = [_is_tree(entry) for entry in entries]

        if prune_identical and all(is_trees) and all_eq(entries):
            continue

        trees = [is_tree and store[entry.sha] or None for is_tree,entry in zip(is_trees,entries)]

        path = first_nonempty([entry.path for entry in entries])
        todo.extend(reversed(_merge_entries(path, trees)))
        yield tuple(entries)

def merge_trees(store, base, mine, theirs):
    ''' takes tree ids for base, mine, and theirs.  merge trees into current working tee'''
    num_conflicts=0
    added=[]
    removed=[]
    w=walk_trees(store,[base,mine, theirs],True)
    count = 0
    for b,m,t in w:
        
        if _is_tree(b) or _is_tree(m) or _is_tree(t):
        #todo... handle mkdir, rmdir
            continue 
        
        # if mine == theirs match, use either
        elif m==t: 
            if not b.path:
                print('  ',m.path, 'was added, but matches already')
            continue    #leave workng tree alone
        # if base==theirs, but not mine, already deleted (do nothing)
        elif b==t and not m.path:
            print('   ',b.path, ' already deleted in head')
            continue
        # if base==mine, but not theirs, delete
        elif b==m and not t.path:
            print('  -',m.path, ' was deleted in theirs.')
            os.remove(m.path)
            removed.append(m.path)
        elif not b.path and m.path and not t.path:  #add in mine
            print('  ',m.path ,'added in mine')
            continue 
        elif not b.path and t.path and not m.path: # add theirs to mine
            # add theirs
            print('  +',t.path, ': adding to head')
            with io_open(t.path,'w') as f:
                f.write(store[t.sha].data)
            added.append(t.path)
        elif not m == t: # conflict
            print('  ?',m.path, ': merging conflicts')
            result=diff3.merge(store[m.sha].data.splitlines(True)
                        ,store[b.sha].data.splitlines(True) if b.sha else ['']
                        ,store[t.sha].data.splitlines(True))
            mergedfile=result['body']
            had_conflict=result['conflict']
            with io_open(m.path,'w') as f:
                for line in mergedfile:
                    f.write(line)
            if had_conflict:
                num_conflicts+=1
                print('    !!! {} had a conflict that could not be resolved.\n    conflict markers added to file in working tree.\n    you need to resolve manually '.format(m.path))
            added.append(m.path)
    return num_conflicts, added, removed

def mergecommits(store,base,mine,theirs):
    merge_trees(store,store[base].tree,store[mine].tree,store[theirs].tree)
    
def merge(args):
    helptext='''git merge' [--msg <msg>] [<commit>]
    git merge --abort\n
    
    merges <commit> into HEAD, or remote tracking branch if commit not specified.
    <commit> can be a local or remote ref, or an existing commit sha.

    merge will handle unambiguous conflicts between head and other 
    merge head, and will insert conflict markers if conflicts cannot be resolved.  
    note that the strategy used will prefer changes in the local head.  
    for instance, if HEAD deleted a section, while MERGE_HEAD modified the same 
    action, the section will be deleted from the final without indicating a conflict.
      
    be sure to commit any local changes before running merge, as files in working tree (i.e on disk) are changed, and checked in, which will probably overwrite any local uncomitted changes.
    
    note merge will not actually commit anything.  run git commit to commit a successful merge.

    
    --abort will remove the MERGE_HEAD and MERGE_MSG files, and will reset staging area, but wont affect files on disk.  use git reset --hard or git checkout if this is desired.
    '''
    repo=_get_repo()
    print('_'*30)

    parser=argparse.ArgumentParser(prog='merge', usage=helptext)
    parser.add_argument('commit',action='store',nargs='?', help='commit sha, local branch, or remote branch name to merge from')
    parser.add_argument('--msg',nargs=1,action='store',help='commit message to store')
    parser.add_argument('--abort',action='store_true',help='abort in progress merge attempt')
    result=parser.parse_args(args)
    
    if result.abort:
        print('attempting to undo merge.  beware, files in working tree are not touched.  \nused git reset --hard to revert particular files')
        git_reset([])
        os.remove(os.path.join(repo.repo.controldir(),'MERGE_HEAD'))
        os.remove(os.path.join(repo.repo.controldir(),'MERGE_MSG'))

    #todo: check for uncommitted changes and confirm
    
    # first, determine merge head
    merge_head = find_revision_sha(repo,result.commit or get_remote_tracking_branch(repo,repo.active_branch))
    if not merge_head:
        raise GitError('must specify a commit sha, branch, remote tracking branch to merge from.  or, need to set-upstream branch using git branch --set-upstream <remote>[/<branch>]')

    head=find_revision_sha(repo,repo.active_branch)

    base_sha=merge_base(repo,head,merge_head)[0]  #fixme, what if multiple bases

    if base_sha==head:
        print('Fast forwarding {} to {}'.format(repo.active_branch,merge_head))
        repo.refs['HEAD']=merge_head
        return 
    if base_sha == merge_head:
        print('head is already up to date')
        return  
    
    print('merging <{}> into <{}>\n{} commits ahead of merge base <{}> respectively'.format(merge_head[0:7],head[0:7],count_commits_between(repo,merge_head,head),base_sha[0:7]))
    base_tree=repo[base_sha].tree
    merge_head_tree=repo[merge_head].tree
    head_tree=repo[head].tree

    num_conflicts,added,removed=merge_trees(repo.repo.object_store, base_tree,head_tree,merge_head_tree)
    # update index
    if added: 
        porcelain.add(repo.path, added)
    if removed: 
        porcelain.rm(repo.path, removed)

    repo.repo._put_named_file('MERGE_HEAD',merge_head)
    repo.repo._put_named_file('MERGE_MSG','Merged from {}({})'.format(merge_head, result.commit))
    print('Merge complete with {} conflicted files'.format(num_conflicts))
    print('''Merged files were added to the staging area, but have not yet been comitted.   
    Review changes (e.g.   git diff   or   git diff>changes.txt; edit changes.txt    ), and 
    resolve any conflict markers before comitting.  
    
    Use   git add     on any files updated after resolving conflicts.  
    Run   git commit  to complete the merge process.
    
    ''')

        
if __name__=='__main__':
    import sys
    merge(sys.argv[1:])
    