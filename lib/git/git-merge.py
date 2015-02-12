from dulwich.diff_tree import _tree_entries, _NULL_ENTRY, TreeEntry, _is_tree
from gittle import Gittle
import stat
import diff3
from gitutils import _get_repo, find_revision_sha, can_ff, merge_base, count_commits_between, is_ancestor, get_remote_tracking_branch, GitError



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
    """Recursively walk all the entries of two trees.

    Iteration is depth-first pre-order, as in e.g. os.walk.

    :param store: An ObjectStore for looking up objects.
    :param tree1_id: The SHA of the first Tree object to iterate, or None.
    :param tree2_id: The SHA of the second Tree object to iterate, or None.
    :param prune_identical: If True, identical subtrees will not be walked.
    :return: Iterator over Pairs of TreeEntry objects for each pair of entries
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

    w=walk_trees(store,[base,mine, theirs],True)

    for b,m,t in w:
        if _is_tree(b) or _is_tree(m) or _is_tree(t):
        #todo... handle mkdir, rmdir
            continue 
        
        # if mine == theirs match, use either
        elif m==t: 
            continue    #leave workng tree alone
        # if base==theirs, but not mine, already deleted (do nothing)
        elif b==t and not m:
            continue
        # if base==mine, but not theirs, delete
        elif b==m and not t:
            os.remove(m.path)
        elif not b and m and not t:  #add in mine
            continue 
        elif not b and t and not m: # add theirs to mine
            # add theirs
            with open(t.path,'w') as f:
                f.write(store[t.sha].data)
        elif not m == t: # conflict
            print 'merging...'
            result=diff3.merge(store[m.sha].data.splitlines(True)
                        ,store[b.sha].data.splitlines(True)
                        ,store[t.sha].data.splitlines(True))
            mergedfile=result['body']
            had_conflict=result['conflict']
            with open(m.path,'w') as f:
                for line in mergedfile:
                    f.write(line)
            if had_conflict:
                print('{} had a conflict.  conflict markers added.  resolve manually '.format(m.path))
            
def mergecommits(store,base,mine,theirs):
    merge_trees(store,store[base].tree,store[mine].tree,store[theirs].tree)
    
def merge(args):
    ''''git merge' [-n] [--stat] [--no-commit] [--squash] [--[no-]edit]
	[-s <strategy>] [-X <strategy-option>] [-S[<key-id>]]
	 [-m <msg>] [<commit>...]
    'git merge' <msg> HEAD <commit>...
    'git merge' --abort
    '''
    repo=_get_repo()
    
    default_merge_head = get_remote_tracking_branch(repo.active_branch)
    
    parser=argparse.ArgumentParser(prog='merge')
    parser.add_argument('commit',action='store',nargs='?')
    result=parser.parse_args(args)
    
    #todo: check for uncommitted changes and confirm
    
    # first, determine merge head
    merge_head = find_revision_sha(result.commit or default_merge_head)
    head=find_revision_sha(repo.active_branch)
    if can_ff(head,merge_head):
        print 'Fast forwarding {} to {}'.format(repo.active_branch,merge_head)
        repo.refs[head]=repo.refs[merge_head]
        return 
    if count_commits_between(merge_head,head)[0]:
        print 'head is already up to date'
        return  
        
    base_sha=merge_base(head,merge_head)[0]  #fixme, what if multiple bases
    
    merge_head_sha=find_revision_sha(merge_head)
    head_sha=find_revision_sha(head)
    base_tree=repo[repo[base_sha].tree]
    merge_head_tree=repo[repo[merge_head].tree]
    head_tree=repo[repo[head_sha].tree]
    
    merge_trees(base_tree,head_tree,merge_head_tree)
        
if __name__=='__main__':
    import sys

    print sys.argv
    repo=Gittle('.')
    store=repo.repo.object_store


    mergecommits(store, *sys.argv[1:])
    
