# -*- coding: utf-8 -*-
'''
Distributed version control system

Commands:
    init:  git init <directory> - initialize a new Git repository
    add: git add <file1> .. [file2] .. - stage one or more files
    rm: git rm <file1> .. [file2] .. - unstage one or more files
    commit: git commit <message> <name> <email> - commit staged files
    clone: git clone <url> [path] - clone a remote repository
    log: git log - Options:\n\t[-l|--length  numner_of _results]\n\t[--oneline Print commits in a concise {commit} {message} form]\n\t[-f|--format format string can use {message}{author}{author_email}{committer}{committer_email}{merge}{commit}]\n\t[-o|--output]  file_name
    ls_files: git ls_file - list files in the index and the working tree
    push: git push [http(s)://<remote repo>] [-u username[:password]] - push changes back to remote
    pull: git pull [http(s)://<remote repo> or remote] - pull changes from a remote repository
    merge: git merge <merge_commit> - merge another branch or commit and head into current working tree.   see git merge -h
    fetch: git fetch [uri or remote] - fetch changes from remote
    checkout: git checkout <branch> - check out a particular branch in the Git tree
    branch: git branch - show branches
    remote: git remote [remotename remoteuri]- list or add remote repos
    status: git status - show status of files (staged unstaged untracked)
    reset: git reset - reset a repo to its pre-change state
    diff: git diff - show changes in staging area
    help: git help
'''
from __future__ import print_function

import argparse
import os
import subprocess
import sys
from getpass import getpass

from six import StringIO
from six.moves import input
from six.moves.urllib.parse import urlparse, urlunparse
from six import iteritems

import console
import editor  # for reloading current file
import keychain

_stash = globals()['_stash']
SAVE_PASSWORDS = True

# temporary -- install required modules
# needed for dulwich: subprocess needs to have Popen
if not hasattr(subprocess, 'call'):

    def Popen(*args, **kwargs):
        pass

    def call(*args, **kwargs):
        return 0

    subprocess.Popen = Popen
    subprocess.call = call
DULWICH_URL = 'https://github.com/dedsecer/dulwich/archive/checkout.zip'
REQUIRED_DULWICH_VERSION = (0, 20, 24)
AUTODOWNLOAD_DEPENDENCIES = True

if AUTODOWNLOAD_DEPENDENCIES:
    libpath = os.path.join(os.environ['STASH_ROOT'], 'lib')
    sys.path.insert(1, libpath)
    download_dulwich = False

    # DULWICH
    try:
        import dulwich
        from dulwich.client import default_user_agent_string
        from dulwich import porcelain
        from dulwich.repo import Repo
        if not dulwich.__version__ == REQUIRED_DULWICH_VERSION:
            print(
                'Dulwich version was {}. Required is {}. Attempting to reload'.format(
                    dulwich.__version__,
                    REQUIRED_DULWICH_VERSION
                )
            )
            for m in [m for m in sys.modules if m.startswith('dulwich')]:
                del sys.modules[m]
            import dulwich
            from dulwich.client import default_user_agent_string
            from dulwich import porcelain
            from dulwich.repo import Repo
            if not dulwich.__version__ == REQUIRED_DULWICH_VERSION:
                print('Could not find correct version. Will download proper fork now')
                download_dulwich = True
            else:
                print('Correct version loaded.')
    except ImportError:
        print('dulwich was not found. Will attempt to download.')
        download_dulwich = True
    try:
        if download_dulwich:
            if not input('Need to download dulwich. OK to download [y/n]?') == 'y':
                raise ImportError()
            _stash('wget {} -o $TMPDIR/dulwich.zip'.format(DULWICH_URL))
            _stash('unzip $TMPDIR/dulwich.zip -d $TMPDIR/dulwich')
            _stash('rm -r $STASH_ROOT/lib/dulwich.old')
            _stash('mv $STASH_ROOT/lib/dulwich $STASH_ROOT/lib/dulwich.old')
            _stash('mv $TMPDIR/dulwich/dulwich $STASH_ROOT/lib/')
            _stash('rm  $TMPDIR/dulwich.zip')
            _stash('rm -r $TMPDIR/dulwich')
            _stash('rm -r $STASH_ROOT/lib/dulwich.old')
            try:
                # dulwich might have already been in site-packages for instance.
                # So, some acrobatic might be needed to unload the module
                if 'dulwich' in sys.modules:
                    for m in [m for m in sys.modules if m.startswith('dulwich')]:
                        del sys.modules[m]
                import dulwich
            except NameError:
                pass
            # try the imports again
            import dulwich
            from dulwich.client import default_user_agent_string
            from dulwich import porcelain
            from dulwich.repo import Repo
    except Exception:
        print(
            '''Still could not import dulwich.
            Perhaps your network connection was unavailable.
            You might also try deleting any existing dulwich versions in site-packages or elsewhere, then restarting pythonista.'''
        )

else:
    import dulwich
    from dulwich.client import default_user_agent_string
    from dulwich import porcelain
    from dulwich.repo import Repo

dulwich.client.get_ssh_vendor = dulwich.client.ParamikoSSHVendor
#  end temporary

command_help = {
    'init': 'initialize a new Git repository',
    'add': 'stage one or more files',
    'rm': 'git rm <file1> .. [file2] .. - unstage one or more files',
    'commit': 'git commit <message> <name> <email> - commit staged files',
    'clone': 'git clone <url> [path] - clone a remote repository',
    'log':
        'git log - Options:\n\t[-l|--length  numner_of _results]\n\t[-f|--format format string can use {message}{author}{author_email}{committer}{committer_email}{merge}{commit}]\n\t[-o|--output]  file_name',
    'ls-files': 'git ls_files - list files in the index and the working tree',
    'push': 'git push [http(s)://<remote repo> or remote] [-u username[:password]] - push changes back to remote',
    'pull': 'git pull [http(s)://<remote repo> or remote] - pull changes from a remote repository',
    'fetch': 'git fetch [uri or remote] - fetch changes from remote',
    'merge': 'git merge <merge_commit> - merge another branch or commit and head into current working tree.   see git merge -h',
    'checkout': 'git checkout <branch> - check out a particular branch in the Git tree. see more in git checkout -h',
    'branch': 'git branch - show and manage branches.  see git branch -h',
    'remote': 'git remote [remotename remoteuri] list or add remote repos ',
    'status': 'git status - show status of files (staged unstaged untracked)',
    'reset':
        'git reset [<commit>] <paths>  reset <paths> in staging area back to their state at <commit>.  this does not affect files in the working area.  \ngit reset [ --mixed | --hard ] [<commit>] reset a repo to its pre-change state. default resets index, but not working tree.  i.e unstages all files.   --hard is dangerous, overwriting index and working tree to <commit>',
    'diff': 'git diff  show changed files in staging area',
    'help': 'git help'
}


# Find a git repo dir
def _find_repo(path):
    try:
        subdirs = next(os.walk(path))[1]
    except StopIteration:  # happens if path is not listable
        return None

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
    repo_dir = _find_repo(os.getcwd())
    if not repo_dir:
        raise Exception("Current directory isn't a git repository")
    return Repo(repo_dir)


def _confirm_dangerous():
    repo = _get_repo()
    status = porcelain.status(repo)
    if status.staged != {'add': [], 'delete': [], 'modify': []} and status.unstaged:
        force = input(
            'WARNING: there are uncommitted modified files and/or staged changes. These could be overwritten by this command. Continue anyway? [y/n] '
        )
        if not force == 'y':
            raise Exception('User cancelled dangerous operation')


def remote_auth(func, **kwargs):
    """Ask for username an password when raised dulwich.client.HTTPUnauthorized

    Args:
        func: function to connect to remote

    note that there must a source or remote_location or repo keyword arguments to be given

    Returns: None
    """
    try:
        func(**kwargs)
    except dulwich.client.HTTPUnauthorized as e:
        # get url
        if 'source' in kwargs.keys():  # arg of clone
            url = kwargs['source']
        elif 'remote_location' in kwargs.keys() and kwargs['remote_location']:  # arg of pull,fetch and push
            url = kwargs['remote_location']

        elif 'repo' in kwargs.keys():
            repo = kwargs['repo']
            remote = porcelain.get_branch_remote(repo)
            url = repo.get_config().get((b'remote', remote), b'url').decode()
            kwargs['remote_location'] = url
        else:
            raise e

        if url.split('/')[0] == 'https:' or url.split('/')[0] == 'http:':
            username = input('Username for \'%s//%s\':' % (url.split('/')[0], url.split('/')[2]))
            password = getpass('Password for \'https://%s@%s\':' % (username, url.split('/')[2]))
            return func(username=username, password=password, **kwargs)
        else:
            raise e


def match_commit_sha(repo, short_sha: bytes):
    if len(short_sha) < 4:
        raise TypeError('short_sha must more than 4')
    for entry in repo.get_walker():
        if short_sha in entry.commit.id:
            return entry.commit.id
    raise Exception('the input short sha do not match any commit')

def refresh_editor():
    #reload current file in editor
    # TODO: only reload if the file was recently updated...
    try:
        sel = editor.get_selection()
        editor.open_file(editor.get_path())
        import time
        time.sleep(0.5)  #let the file load
        editor.replace_text(sel[0], sel[0], '')  #force scroll
        editor.set_selection(sel[0], sel[1])
    except:
        print('Could not refresh editor.  continuing anyway')


def git_init(args):
    if len(args) == 0:
        porcelain.init()
    elif len(args) == 1:
        porcelain.init(args[0])
    else:
        print(command_help['init'])


def git_status(args):
    if len(args) == 0:
        repo = _get_repo()
        status = porcelain.status(repo)
        clean = True
        try:
            print('On branch %s' % (porcelain.active_branch(repo).decode()))
        # HEAD detached
        except IndexError:
            print('HEAD detached at %s' % (repo.head()[0:7].decode()))

        if not status.staged == {'add': [], 'delete': [], 'modify': []}:
            print('STAGED: ', end='')
            for k, v in iteritems(status.staged):
                if v:
                    print('%s: %s  ' % (k, v), end='')
            print('')
            clean = False

        if status.unstaged:
            print('UNSTAGED: ', end='')
            print(status.unstaged)
            clean = False

        if status.untracked:
            print('UNTRACKED: ', end='')
            print(status.untracked)
            clean = False

        if clean:
            print('nothing to commit, working tree clean')

    else:
        print(command_help['status'])


def git_remote_add(args):
    repo = _get_repo()
    porcelain.remote_add(repo, args[0], args[1])
    print("remote '%s' have been added" % (args[0]))


def git_remote_list(args):
    repo = _get_repo()
    config = repo.get_config()
    for keys, values in list(config.items()):
        if keys[0] == b'remote':
            print(keys[1].decode() + '  ' + values[b'url'].decode())


def git_remote(args):
    # TODO: remove remote
    description = """
    list or add remote repos
    git remote - print a list of remote
    git remote add <remote_name> <url> - Add a remote named <remote_name> for the repository at <url>.
    """
    parser = argparse.ArgumentParser(
        prog='git remote',
        description=description
    )
    subparser = parser.add_subparsers()
    add_parser = subparser.add_parser('add', help='git remote add <remote_name> <url> - Add a remote named <remote_name> for the repository at <url>.')
    parser.set_defaults(func=git_remote_list)
    add_parser.set_defaults(func=git_remote_add)
    result, args = parser.parse_known_args(args)
    result.func(args)

    # remove_parser = subparser.add_parser('remove', help='')
    '''List remote repos'''
    # if len(args) == 0:
    #     repo = _get_repo()
    #     for key, value in repo.remotes.items():
    #         print('{} {}'.format(key, value))
    # elif len(args) == 2:
    #     repo = _get_repo()
    #     repo.add_remote(args[0], args[1])
    # else:
    #     print(command_help['remote'])


def git_add(args):
    if len(args) > 0:
        repo = _get_repo()
        old_cwd = os.getcwd()
        os.chdir(repo.path)
        for file in args:
            if file.encode() in repo.open_index():
                porcelain.add(repo, [file])
                print('{0} Added'.format(file))
            else:
                print('{} does not exist. skipping'.format(file))
        os.chdir(old_cwd)

    else:
        print(command_help['add'])


def git_unstage(args):
    for file in args:
        repo = _get_repo()
        repo.unstage([file.encode() for file in args])
        print('unstaged ' + file)


def git_rm(args):
    if len(args) > 0:
        repo = _get_repo()
        cwd = os.getcwd()
        args = [os.path.join(os.path.relpath(cwd, repo.path), x) if not os.path.samefile(cwd, repo.path) else x for x in args]
        for file in args:
            print('Removing {0}'.format(file))
            porcelain.rm(repo.path, args)

    else:
        print(command_help['rm'])


def launch_subcmd(cmd, args):
    cmdpath = os.path.join(os.environ['STASH_ROOT'], 'lib', 'git', cmd)

    _stash(cmdpath + ' ' + ' '.join(args))


def git_branch(args):
    repo = _get_repo()

    parser = argparse.ArgumentParser(prog='git branch', description="List, create, or delete branches")
    parser.add_argument('branch', default='', nargs='?')
    parser.add_argument('-l', '--list', action='store_true', help='List branches')
    parser.add_argument('-d', '--delete', action='store_true', help='Delete a branch')
    result = parser.parse_args(args)

    if result.list or not args:
        try:
            active_branch = porcelain.active_branch(repo)

        except IndexError:
            active_branch = None
            print('* (HEAD detached at %s)' % (repo.head()[0:7].decode()))

        for branch in porcelain.branch_list(repo):
            if branch == active_branch:
                print('* ' + branch.decode())
            else:
                print('  '+branch.decode())

    elif result.delete and result.branch:
        porcelain.branch_delete(repo, result.branch)
        print('Deleted branch %s (was %s)' % (result.branch, repo.refs[b'refs/heads/' + result.branch][0:7].encode()))
    elif result.branch:
        porcelain.branch_create(repo, result.branch)
        print('Created branch %s' % (result.branch))


def git_merge(args):
    launch_subcmd('git-merge.py', args)


def git_reset(args):
    parser = argparse.ArgumentParser(
        prog='git reset',
        usage='git reset [commit] [paths]',
        description="reset a repo to its pre-change state (only hard reset are supported)"
    )

    parser.add_argument('commit', nargs='?', action='store', default='HEAD')
    parser.add_argument('paths', nargs='*')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--hard', action='store_true')
    mode.add_argument('--mixed', action='store_true')
    mode.add_argument('--soft', action='store_true')

    result = parser.parse_args(args)
    commit = result.commit.encode()
    paths = result.paths
    repo = _get_repo()

    if result.mixed or result.soft:
        print('only hard reset are supported now')
    
    if result.hard and result.paths:
        raise Exception('Cannot do hard reset with paths.')

    if commit == b'HEAD':
        commit = repo.head()
    # convert branch name to full sha
    elif commit in porcelain.branch_list(repo):
        commit = repo.refs[b'refs/heads/' + commit]
    # match short sha to full sha
    elif len(commit) >= 4 and len(commit) <= 40:
        commit = match_commit_sha(repo, commit)
    else:
        print(commit.decode(), 'is not a valid branchname. head was not updated')

    if paths:
        for path in paths:
            porcelain.reset_file(repo, path, target=commit)
    else:
        porcelain.reset(repo, mode='hard', treeish=commit)
    refresh_editor()
    print('updated HEAD to ', commit.decode())


def get_config_or_prompt(repo, section, name, prompt, save=None):
    config = repo.repo.get_config_stack()
    try:
        value = config.get(section, name)
    except KeyError:
        value = input(prompt).encode()
        if not save:
            reply = input('Save this setting? [y/n]')
            save = reply == 'y'
        if save:
            reply = input('Save globally (~/.gitconfig) for all repos? [y/n]')
            saveglobal = reply == 'y'
            if saveglobal:
                globalcfg = config.default_backends()
                if not globalcfg:
                    open(os.path.expanduser('~/.gitconfig'), 'w').close()  # create file
                    globalcfg = config.default_backends()
                globalcfg = globalcfg[0]
                globalcfg.set(section, name, value)
                globalcfg.write_to_path()
            else:
                config.set(section, name, value)
                config.writable.write_to_path()
    return value


def git_commit(args):
    ap = argparse.ArgumentParser('Commit current working tree.')
    ap.add_argument('-m', '--message', default=None, nargs='?', help='commit message')
    ap.add_argument('--author', default=None, help='Override the commit author. Specify an explicit author using the "USER <EMAIL>" format.')
    ns = ap.parse_args(args)

    repo = _get_repo()

    file_changed = 0
    for value in porcelain.status(repo).staged.values():
        file_changed += len(value)
    sha = porcelain.commit(repo, message=ns.message, author=ns.author).decode()
    print('[%s %s] %s ,%i file changed' % (porcelain.active_branch(repo).decode(), sha[0:7], ns.message, file_changed))


def git_clone(args):
    if len(args) > 0:
        url = args[0]
        if len(args) > 1:
            target = args[1]
        else:
            target = os.path.split(args[0])[-1]
            if target.endswith('.git'):
                target = target[:-4]
        remote_auth(porcelain.clone, source=url)
    else:
        print(command_help['clone'])


def git_pull(args):
    parser = argparse.ArgumentParser(
        prog='git pull',
        usage='git pull [url]',
        description="pull changes from a remote repository"
    )
    parser.add_argument('url', type=str, nargs='?', help='URL to pull from')
    result = parser.parse_args(args)

    repo = _get_repo()
    _confirm_dangerous()
    if not result.url:
        result.url = porcelain.get_branch_remote(repo)

    remote_auth(porcelain.pull, repo=repo, remote_location=result.url)

    print('pull successed!')


def git_fetch(args):
    parser = argparse.ArgumentParser(
        prog='git fetch',
        usage='git fetch [http(s)://<remote repo> or remotename]',
        description="Push to a remote repository"
    )
    parser.add_argument('url', type=str, nargs='?', help='URL to fetch')
    result = parser.parse_args(args)

    repo = _get_repo()

    if not result.url:
        result.url = porcelain.get_branch_remote(repo)
    remote_auth(porcelain.fetch, repo=repo, remote_location=result.url)
    print('Fetch successful')


def git_push(args):
    parser = argparse.ArgumentParser(
        prog='git push',
        usage='git push [url]',
        description="Push to a remote repository"
    )
    parser.add_argument('url', type=str, nargs='?', help='URL to push to')
    result = parser.parse_args(args)

    repo = _get_repo()
    _confirm_dangerous()

    branch_name = os.path.join(b'refs', b'heads', porcelain.active_branch(repo))  # b'refs/heads/%s' % repo.active_branch
    print("Attempting to push to: {0}, branch: {1}".format(result.url, branch_name))

    remote_auth(porcelain.push, repo=repo, remote_location=result.url)

    print('push successed!')


def git_log(args):
    parser = argparse.ArgumentParser(description='git log arg parser')
    parser.add_argument('-f', '--format', action='store', dest='format', default=False)
    parser.add_argument('-o', '--output', action='store', dest='output', type=argparse.FileType('w'), default=sys.stdout)
    parser.add_argument('-r', action='store_true', default=True, help='reverse the output, default is true')
    parser.add_argument('-l', '--length', action='store', type=int, dest='max_entries', default=5)

    parser.add_argument('--oneline', action='store_true', dest='oneline', default=False)

    results = parser.parse_args(args)

    try:
        repo = _get_repo()
        outstream = StringIO()
        porcelain.log(repo, max_entries=results.max_entries, reverse=results.r, outstream=outstream)

        if not results.oneline:
            print(outstream.getvalue())
        else:

            last_commit = ''
            last_printed = ''
            start_message = False
            for line in outstream.getvalue().split('\n'):
                if line.startswith('commit:'):
                    tokens = line.split(' ')
                    last_commit = tokens[-1][:7]

                elif line.startswith('-------------'):
                    last_commit = ''
                    start_message = False

                elif line == '' and start_message is False:
                    start_message = True

                elif last_commit == last_printed and start_message is True:
                    continue

                elif start_message is True and not line.startswith('---------'):
                    print('{} {}'.format(last_commit, line))
                    last_printed = last_commit
                    start_message = False

    except ValueError:
        print(command_help['log'])


def git_ls_files(args):
    repo = _get_repo()
    for file in porcelain.ls_files(repo):
        print(file.decode())


def git_diff(args):
    '''prints diff of currently staged files to console.. '''
    repo = _get_repo()

    index = repo.open_index()
    store = repo.object_store
    index_sha = index.commit(store)
    # tree_ver=store[tree.lookup_path(store.peel_sha,file)[1]].data
    porcelain.diff_tree('.', repo[repo['HEAD'].tree].id, repo[index_sha].id, sys.stdout)


def git_checkout(args):
    description = """
    git checkout -b <branch>: create new branch and checkout to new branch
    git checkout <branch>: checkout a particular branch in the Git tree
    git checkout <commit>:   Prepare to work on top of <commit>, by detaching HEAD at it
    git checkout <pathspec>: checkout the pathspec to HEAD
    git checkout <branch> -- <pathspec>: checkout the <pathspec> to <branch>
    git checkout <tree-ish> -- <pahtspec>: checkout the <pathspec> to <tree-ish>
    """

    repo = _get_repo()
    branch_list = porcelain.branch_list(repo)

    parser = argparse.ArgumentParser(prog='git checkout', description=description)

    if '--' not in args:
        parser.add_argument('-b', action='store', nargs='?')
        parser.add_argument('target', default='', nargs='+')
        result = parser.parse_args(args)
        # porcelain.update_head to HEAD will broke the repo
        if result.target == 'HEAD':
            raise Exception('checkout to HEAD is not support now')

        if len(result.target) == 1:
            result.target = result.target[0]
            result.target = result.target.encode()
        # match short sha to full sha
        if result.target not in branch_list and not result.b and result.target not in repo.open_index() and len(result.target) != 40:
            result.target = match_commit_sha(repo, result.target)

        # create new branch and checkout to new branch
        if result.b:
            porcelain.branch_create(repo, result.b)
            porcelain.checkout(repo, result.b.encode())
            print("Switched to a new branch '%s'" % (result.b))
        # checkout specified paths to HEAD
        elif isinstance(result.target, list):
            for file in result.target:
                porcelain.reset_file(repo, file.decode(), b'HEAD')
        # checkout specified path to HEAD
        elif result.target in porcelain.ls_files(repo):
            porcelain.reset_file(repo, result.target.decode(), b'HEAD')
        # branch
        elif result.target in porcelain.branch_list(repo):
            porcelain.checkout(repo, result.target)
            print("Switched to a new branch '%s'" % (result.target.decode()))
        # full commit sha or short commit sha
        elif len(result.target) == 40 or result.target not in porcelain.branch_list(repo):
            porcelain.checkout(repo, result.target)
            print("HEAD is now at %s" % (repo.head()[0:7].decode()))

    # checkout specified path to HEAD
    elif '--' in args[0]:
        parser.add_argument('pathspec', default='', nargs='+')
        result = parser.parse_args(args)

        for file in result.pathspec:
            porcelain.reset_file(repo, file, b'HEAD')
            print("file '%s' reset to HEAD" % (file))

    # checkout specified path to branch or commit sha
    elif '--' in args[1]:
        parser.add_argument('target', default='', nargs='?')
        parser.add_argument('pathspec', default='', nargs='+')
        result = parser.parse_args(args)
        if result.target == 'HEAD':
            raise Exception('checkout to HEAD is not support now')

        if result.target not in branch_list and len(result.target) != 40:
            result.target = match_commit_sha(repo, result.target)

        if not result.pathspec:
            porcelain.checkout(repo, result.target.encode())
        for file in result.pathspec:
            porcelain.reset_file(repo, file, result.target.encode())
            print("file '%s' reset to %s" % (file, result.target))
    refresh_editor()


def git_help(args):
    print('help:')
    for key, value in command_help.items():
        print(value)


commands = {
    'init': git_init,
    'add': git_add,
    'unstage': git_unstage,
    'rm': git_rm,
    'commit': git_commit,
    'clone': git_clone,
    'log': git_log,
    'ls-files': git_ls_files,
    'push': git_push,
    'pull': git_pull,
    'fetch': git_fetch,
    'branch': git_branch,
    'merge': git_merge,
    'checkout': git_checkout,
    'remote': git_remote,
    'reset': git_reset,
    'status': git_status,
    'diff': git_diff,
    'help': git_help,
}
if __name__ == '__main__':
    if len(sys.argv) == 1:
        sys.argv = sys.argv + ['-h']

    ap = argparse.ArgumentParser()
    subparser = ap.add_subparsers()
    for command, function in commands.items():
        # sp = subparser.add_parser(key, help=command_help[key], add_help=False)
        sp = subparser.add_parser(command, add_help=False)
        sp.set_defaults(func=function)
    ns, args = ap.parse_known_args()
    ns.func(args)
