import sys
import os
import dulwich
from dulwich import porcelain
from dulwich.walk import Walker
from gittle import Gittle


class GitError(Exception):
    def __init__(self, arg):
        Exception.__init__(self, arg)


def _find_repo(path):
    subdirs = os.walk(path).next()[1]
    if '.git' in subdirs:
        return path
    else:
        parent = os.path.dirname(path)
        if parent == path:
            return None
        else:
            return _find_repo(parent)

# Get the parent git repo, if there is one


def _get_repo():
    return Gittle(_find_repo(os.getcwd()))


def any_one(iterable):
    it = iter(iterable)
    return any(it) and not any(it)


def find_revision_sha(repo, rev):
    '''rev may refer to the following ways to "spell" a commit object:
    <sha1>  full or abbreviated sha, only if unique
    <ref>  search in local refs, then remote refs.
      . If '$GIT_DIR/<refname>' exists, that is what you mean (this is usually
    useful only for 'HEAD', 'FETCH_HEAD', 'ORIG_HEAD', 'MERGE_HEAD'
    and 'CHERRY_PICK_HEAD');
    . otherwise, 'refs/<refname>' if it exists;
    . otherwise, 'refs/tags/<refname>' if it exists;
    . otherwise, 'refs/heads/<refname>' if it exists;
    . otherwise, 'refs/remotes/<refname>' if it exists;
    . otherwise, 'refs/remotes/<refname>/HEAD' if it exists.
    '''

    if rev in repo:
        return repo[rev].id

    o = repo.repo.object_store

    returnval = repo.refs.get(rev) or repo.tags.get(
        rev) or repo.branches.get(rev) or repo.remote_branches.get(rev)
    if returnval:
        return returnval
    else:
        shalist = [sha for sha in o if sha.startswith(
            rev) and isinstance(o[sha], dulwich.objects.Commit)]
        if len(shalist) == 1:
            return (shalist[0])
        elif len(shalist) > 1:
            raise GitError('SHA {} is not unique'.format(rev))
        raise GitError('could not find rev {}'.format(rev))


def merge_base(repo, rev1, rev2):
    ''''git merge-base' finds best common ancestor(s) between two commits to use
in a three-way merge.  One common ancestor is 'better' than another common
ancestor if the latter is an ancestor of the former.  A common ancestor
that does not have any better common ancestor is a 'best common
ancestor', i.e. a 'merge base'.  Note that there can be more than one
merge base for a pair of commits.'''
    sha1 = find_revision_sha(repo, rev1)
    sha2 = find_revision_sha(repo, rev2)

    sha2_ancestors, _ = repo.repo.object_store._collect_ancestors([sha2], [])
    merge_bases = []
    queue = [sha1]
    seen = []

    while queue:
        elt = queue.pop()
        if elt not in seen:  # prevent circular
            seen.append(elt)
            if elt in sha2_ancestors:
                merge_bases.append(elt)
            elif repo[elt].parents:
                queue.extend(repo[elt].parents)
    return merge_bases


def count_commits_between(repo, rev1, rev2):
    '''find common ancestor. then count ancestor->sha1, and ancestor->sha2 '''
    sha1 = find_revision_sha(repo, rev1)
    sha2 = find_revision_sha(repo, rev2)
    if sha1 == sha2:
        return (0, 0)
    sha1_ahead = sum(1 for _ in Walker(repo.repo.object_store, [sha1], [sha2]))
    sha1_behind = sum(
        1 for _ in Walker(
            repo.repo.object_store,
            [sha2],
            [sha1]))
    return (sha1_ahead, sha1_behind)


def is_ancestor(repo, rev1, rev2):
    '''return true if rev1 is an ancestor of rev2'''
    sha1 = find_revision_sha(repo, rev1)
    sha2 = find_revision_sha(repo, rev2)
    return True if sha1 in merge_base(repo, sha1, sha2) else False


def can_ff(repo, oldrev, newrev):
    return merge_base(repo, oldrev, newrev) == [oldrev]


def get_remote_tracking_branch(repo, branchname):
    config = repo.repo.get_config()
    try:
        remote = config.get(('branch', branchname), 'remote')
        merge = config.get(('branch', branchname), 'merge')
        remotebranch = merge.split('refs/heads/')[1]
        return remote + '/' + remotebranch
    except KeyError:
        return None
