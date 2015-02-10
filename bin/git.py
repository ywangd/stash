
'''
git
------------
basic git functionality

commands:
    init:  git init <directory> - initialize a new Git repository
    add: git add <file1> .. [file2] .. - stage one or more files
    rm: git rm <file1> .. [file2] .. - unstage one or more files
    commit: git commit <message> <name> <email> - commit staged files
    clone: git clone <url> [path] - clone a remote repository
    modified: git modified - show what files have been modified
    log: git log - Options:\n\t[-l|--length  numner_of _results]\n\t[-f|--format format string can use {message}{author}{author_email}{committer}{committer_email}{merge}{commit}]\n\t[-o|--output]  file_name
    push: git push [http(s)://<remote repo>] [-u username[:password]] - push changes back to remote
    pull: git pull [http(s)://<remote repo> or remote] - pull changes from a remote repository
    checkout: git checkout <branch> - check out a particular branch in the Git tree
    branch: git branch - show branches
    remote: git remote [remotename remoteuri]- list or add remote repos 
    status: git status - show status of files (staged unstaged untracked)
    reset: git reset - reset a repo to its pre-change state
    help: git help
'''

SAVE_PASSWORDS = True

import argparse
import getpass
import urlparse,urllib2,keychain
import sys,os,posix

# temporary -- install required modules

GITTLE_URL='https://github.com/jsbain/gittle/archive/master.zip'
FUNKY_URL='https://github.com/FriendCode/funky/archive/master.zip'
DULWICH_URL='https://github.com/transistor1/dulwich/archive/master.zip'

if True:
    libpath=os.path.join(_stash.runtime.envars['STASH_ROOT'] ,'lib')
    if not libpath in sys.path:
        sys.path.insert(1,libpath)
    try:  
        import dulwich
        from dulwich.client import default_user_agent_string
        from dulwich import porcelain
        from dulwich.index import index_entry_from_stat
    except ImportError:
        _stash('wget {} -o $TMPDIR/dulwich.zip'.format(DULWICH_URL))
        _stash('unzip $TMPDIR/dulwich.zip -d $TMPDIR/dulwich')
        _stash('mv $TMPDIR/dulwich/dulwich $STASH_ROOT/lib/')
        _stash('rm  $TMPDIR/dulwich.zip')
        _stash('rm -r $TMPDIR/dulwich')
        import dulwich
        from dulwich import porcelain
        from dulwich.client import default_user_agent_string
    
    try:
        gittle_path=os.path.join(libpath,'gittle')
        funky_path=os.path.join(libpath,'funky')
        import gittle
        Gittle=gittle.Gittle
    except ImportError:
        _stash('wget {} -o $TMPDIR/gittle.zip'.format(GITTLE_URL))
        _stash('unzip $TMPDIR/gittle.zip -d $TMPDIR/gittle')
        _stash('mv $TMPDIR/gittle/gittle $STASH_ROOT/lib')
        _stash('wget {} -o $TMPDIR/funky.zip'.format(FUNKY_URL))
        _stash('unzip $TMPDIR/funky.zip -d $TMPDIR/funky')
        _stash('mv $TMPDIR/funky/funky $STASH_ROOT/lib')
        _stash('rm  $TMPDIR/gittle.zip')
        _stash('rm  $TMPDIR/funky.zip')
        _stash('rm -r $TMPDIR/gittle')
        _stash('rm -r $TMPDIR/funky')
        import gittle
        Gittle=gittle.Gittle
    ## end install modules
else:
    from dulwich import porcelain
    from dulwich.client import default_user_agent_string
    from dulwich.index import index_entry_from_stat
    from gittle import Gittle

#  end temporary



command_help={    'init':  'initialize a new Git repository'
    ,'add': 'stage one or more files'
    ,'rm': 'git rm <file1> .. [file2] .. - unstage one or more files'
    ,'commit': 'git commit <message> <name> <email> - commit staged files'
    ,'clone': 'git clone <url> [path] - clone a remote repository'
    ,'modified': 'git modified - show what files have been modified'
    ,'log': 'git log - Options:\n\t[-l|--length  numner_of _results]\n\t[-f|--format format string can use {message}{author}{author_email}{committer}{committer_email}{merge}{commit}]\n\t[-o|--output]  file_name'
    ,'push': 'git push [http(s)://<remote repo> or remote] [-u username[:password]] - push changes back to remote'
    ,'pull': 'git pull [http(s)://<remote repo> or remote] - pull changes from a remote repository'
    ,'fetch': 'git fetch [uri or remote] - fetch changes from remote'
    ,'checkout': 'git checkout <branch> - check out a particular branch in the Git tree'
    ,'branch': 'git branch - show and manage branches.  see git branch -h'
    ,'remote': 'git remote [remotename remoteuri] list or add remote repos '
    ,'status': 'git status - show status of files (staged unstaged untracked)'
    ,'reset': 'git reset [<commit>] <paths>  reset <paths> in staging area back to their state at <commit>.  this does not affect files in the working area.  \ngit reset [ --mixed | --hard ] [<commit>] reset a repo to its pre-change state. default resets index, but not working tree.  i.e unstages all files.   --hard is dangerous, overwriting index and working tree to <commit>'
    ,'help': 'git help'
          }


    
    #Find a git repo dir
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

#Get the parent git repo, if there is one
def _get_repo():
    return Gittle(_find_repo(os.getcwd()))

def _confirm_dangerous():
        repo = _get_repo()
        status=porcelain.status(repo.path)
        if any(status.staged.values()+status.unstaged):
            force=raw_input('WARNING:  there are uncommitted modified files files and/or staged changes.  these could be overwritten by this command.  continue anyway? [y/n] ')
            if not force=='y':
                raise Exception('use cancelled dangerous operation')
                
def unstage(commit='HEAD',paths=[]):
    repo=_get_repo().repo
    for somepath in paths:
        #print path
        path=_get_repo().relpath(somepath)
        full_path = os.path.join(repo.path, path)

        index=repo.open_index()
        tree_id=repo[commit]._tree
        try:
            tree_entry=repo[tree_id].lookup_path(lambda x:repo[x],path)
        except KeyError:
            #if tree_entry didnt exist, this file was being added, so remove index entry
            try:
                del(index[path])
                index.write()
            except KeyError:
                print 'file not in index.',path
            return
            
        try:
            index_entry=list(index[path])
        except KeyError:
            #if index_entry doesnt exist, this file was being removed.  readd it
            if os.path.exists(full_path):
                index_entry=list(index_entry_from_stat(posix.lstat(full_path),tree_entry[1]  ,0    ))
            else:
                index_entry=[[0]*11,tree_entry[1],0]
                
        #update index entry stats to reflect commit
        index_entry[4]=tree_entry[0] #mode
        index_entry[7]=len(repo[tree_entry[1]].data) #size
        index_entry[8]=tree_entry[1] #sha
        index_entry[0]=repo[commit].commit_time #ctime
        index_entry[1]=repo[commit].commit_time #mtime
        index[path]=index_entry
        index.write()

def unstage_all( commit='HEAD'):
    # files to unstage consist of whatever was in new tree, plus whatever was in old index (added files to old branch)
    repo=_get_repo().repo
    index=repo.open_index()
    tree_id=repo[commit]._tree
    for entry in repo.object_store.iter_tree_contents(tree_id):
        unstage(commit,[entry.path])

    for entry in index.iteritems():
        unstage(commit,[entry[0]])

    
def git_init(args):
    if len(args) == 1:
        Gittle.init(args[0])
    else:
        print command_help['init']

def git_status(args):
    if len(args) == 0:
        repo = _get_repo()
        status = porcelain.status(repo.repo)
        print status
    else:
        print command_help['status']

def git_remote(args):
    '''List remote repos'''
    if len(args) == 0:
        repo = _get_repo()
        for key, value in repo.remotes.items():
            print key, value
    elif len(args)==2:
        repo=_get_repo()
        repo.add_remote(args[0],args[1])
    else:
        print command_help['remote']

def git_add(args):
    if len(args) > 0:
        repo = _get_repo()
        cwd = os.getcwd()

        args = [os.path.join(os.path.relpath(cwd, repo.path), x)
                    if not os.path.samefile(cwd, repo.path) else x for x in args]
        for file in args:
            if os.path.exists(file):
                print 'Adding {0}'.format(file)
                porcelain.add(repo.repo, [file])
            else:
                print '{} does not exist. skipping'.format(file)

    else:
        print command_help['add']

def git_rm(args):
    if len(args) > 0:
        repo = _get_repo()
        cwd = os.getcwd()
        args = [os.path.join(os.path.relpath(cwd, repo.path), x)
                    if not os.path.samefile(cwd, repo.path) else x for x in args]
        for file in args:
            print 'Removing {0}'.format(file)
            #repo.rm(args)
            porcelain.rm(repo.repo, args)

    else:
        print command_help['rm']
def launch_subcmd(cmd,args):
    cmdpath=os.path.join(_stash.runtime.envars['STASH_ROOT'],'lib','git',cmd)

    _stash.runtime.exec_py_file(cmdpath, args=args,
                     ins=sys.stdin, outs=sys.stdout, errs=sys.stderr)
    
def git_branch(args):
    launch_subcmd('git-branch.py',args)


def git_reset(args):
    ap=argparse.ArgumentParser('reset')
    ap.add_argument('commit',nargs='?',action='store',default='HEAD')
    ap.add_argument('paths',nargs='*')
    mode=ap.add_mutually_exclusive_group()
    mode.add_argument('--hard',action='store_true',dest='hard')
    mode.add_argument('--mixed',action='store_false',dest='hard')

    ns=ap.parse_args(args)
    
    hard=ns.hard
        
    repo = _get_repo().repo
    #handle optionals
    commit= ns.commit
    # first arg was really a file
    paths=ns.paths or []
    if not commit in _get_repo() and os.path.exists(commit):
        paths=[commit]+paths
        commit = None
    elif not commit in _get_repo() and not os.path.exists(commit):
        raise Exception('{} is not a valid commit or file'.format(commit))
    if not commit:
        commit=repo.refs['HEAD']
    
    if hard:
        _confirm_dangerous()
    # first, unstage index
    if paths:
        unstage(commit,paths)
    else:
        print 'resetting index. please wait'
        unstage_all(commit)
        print 'complete'
    # next, rebuild files
    if hard:
        treeobj=repo[repo[commit].tree]
        
        for path in paths:
            print 'resetting '+path
            relpath=repo.relpath(path)
            file_contents=repo[treeobj[relpath][1]].as_raw_string()
            with open(str(path),'w') as f:
                f.write(file_contents)

def git_commit(args):
    ap=argparse.ArgumentParser('Commit current working tree.')
    ap.add_argument('message',default=None,nargs='?')
    ap.add_argument('name',default=None,nargs='?')
    ap.add_argument('email',default=None,nargs='?')
    ns=ap.parse_args(args)
    if not ns.message:
        ns.message=raw_input('Commit Message: ')
    if not ns.name:
        ns.name=raw_input('Author Name:')
    if not ns.email:
        ns.email=raw_input('Author Email')
     
    try:
        repo = _get_repo()
        author = "{0} <{1}>".format(ns.name, ns.email)
        print porcelain.commit(repo.repo, ns.message, author, author )
    except:
        print 'Error: {0}'.format(sys.exc_value)


def git_clone(args):
    if len(args) > 0:
        url = args[0]

        repo = Gittle.clone(args[0], args[1] if len(args)>1 else '.', bare=False)

        #Set the origin
        config = repo.repo.get_config()
        config.set(('remote','origin'),'url',url)
        config.write_to_path()
    else:
        print command_help['clone']

def git_pull(args):
    if len(args) <= 1:
        repo = _get_repo()
        _confirm_dangerous()
        url = args[0] if len(args)==1 else repo.remotes.get('origin','')
        
        if url in repo.remotes:
            origin=url
            url=repo.remotes.get(origin)
        
        if url:
            repo.pull(origin_uri=url)
        else:
            print 'No pull URL.'
    else:
        print command_help['git pull']

def git_fetch(args): 
    parser = argparse.ArgumentParser(prog='git fetch'
                                     , usage='git fetch [http(s)://<remote repo> or remotename] [-u username[:password]]'
                                     , description="Push to a remote repository")
    parser.add_argument('url', type=str, nargs='?', help='URL to push to')
    parser.add_argument('-u', metavar='username[:password]', type=str, required=False, help='username[:password]')
    result = parser.parse_args(args)
    
    repo = _get_repo()
    
    origin='origin'
    if not result.url:
        result.url = repo.remotes.get('origin','')
    if result.url in repo.remotes:
        origin=result.url
        result.url=repo.remotes.get(origin)
    remote_refs=porcelain.fetch(repo.repo.path,result.url)

    remote_tags = gittle.utils.git.subrefs(remote_refs, 'refs/tags')
    remote_heads = gittle.utils.git.subrefs(remote_refs, 'refs/heads')
        
    # Filter refs
    clean_remote_tags = gittle.utils.git.clean_refs(remote_tags)
    clean_remote_heads = gittle.utils.git.clean_refs(remote_heads)

    # Base of new refs
    heads_base = 'refs/remotes/' + origin

    # Import branches
    repo.import_refs(
        heads_base,
        clean_remote_heads
    )
    for k,v in clean_remote_heads.items():
        print 'imported {}/{} {}'.format(heads_base,k,v) 
    # Import tags
    repo.import_refs(
        'refs/tags',
        clean_remote_tags
    )
    for k,v in clean_remote_tags.items():
        print 'imported {}/{} {}'.format('refs/tags',k,v) 
    #delete unused remote refs
    for k in gittle.utils.git.subrefs(repo.refs,heads_base):
        if k not in gittle.utils.git.subrefs(clean_remote_heads,origin):
            del repo.refs['/'.join([heads_base,k])]
    

def git_push(args):
    parser = argparse.ArgumentParser(prog='git push'
                                     , usage='git push [http(s)://<remote repo> or remote] [-u username[:password]]'
                                     , description="Push to a remote repository")
    parser.add_argument('url', type=str, nargs='?', help='URL to push to')
    parser.add_argument('-u', metavar='username[:password]', type=str, required=False, help='username[:password]')
    result = parser.parse_args(args)

    user, sep, pw = result.u.partition(':') if result.u else (None,None,None)

    repo = _get_repo()

    origin='origin'
    if not result.url:
        result.url = repo.remotes.get('origin','')
    if result.url in repo.remotes:
        origin=result.url
        result.url=repo.remotes.get(origin)

    branch_name = os.path.join('refs','heads', repo.active_branch)  #'refs/heads/%s' % repo.active_branch

    print "Attempting to push to: {0}, branch: {1}".format(result.url, branch_name)

    netloc = urlparse.urlparse(result.url).netloc

    keychainservice = 'stash.git.{0}'.format(netloc)

    if sep and not user:
        # -u : clears keychain for this server
        for service in keychain.get_services():
            if service[0]==keychainservice:
                keychain.delete_password(*service)

    #Attempt to retrieve user
    if not user and SAVE_PASSWORDS:
        try:
            user = dict(keychain.get_services())[keychainservice]
        except KeyError:
            user = raw_input('enter username:')
            pw = raw_input('enter password')
            #user, pw = console.login_alert('Enter credentials for {0}'.format(netloc))

    if user:
        if not pw and SAVE_PASSWORDS:
            pw = keychain.get_password(keychainservice, user)

        #Check again, did we retrieve a password?
        if not pw:
            user, pw = console.login_alert('Enter credentials for {0}'.format(netloc), login=user)
            #pw = getpass.getpass('Enter password for {0}: '.format(user))

        opener = auth_urllib2_opener(None, result.url, user, pw)

        porcelain.push(repo.repo, result.url, branch_name, opener=opener)
        keychain.set_password(keychainservice, user, pw)

    else:
        porcelain.push(repo.repo, result.url, branch_name)

def git_modified(args):
    repo = _get_repo()
    for mod_file in repo.modified_files:
        print mod_file

def git_log(args):
    parser = argparse.ArgumentParser(description='git log arg parser')
    parser.add_argument('-f','--format',
                        action='store',
                        dest='format',
                        default=False)
    parser.add_argument('-o','--output',
                        action='store',
                        dest='output',
                        type=argparse.FileType('w'),
                        default=sys.stdout)

    parser.add_argument('-l','--length',
                        action='store',
                        type=int,
                        dest='max_entries',
                        default=None)

    results = parser.parse_args(args)

    try:
        repo = _get_repo()
        porcelain.log(repo.repo, max_entries=results.max_entries,format=results.format,outstream=results.output)
    except ValueError:
        print command_help['log']



def git_checkout(args):
    if len(args) in [1,2]:
        repo = _get_repo()
        _confirm_dangerous()
            
        if len(args) == 1:
            branchname=args[0]
            if branchname in repo.branches:
                branch_ref=repo._format_ref_branch(branchname)
                repo.repo.refs.set_symbolic_ref('HEAD',branch_ref)
                repo.checkout_all()
            repo.switch_branch('{0}'.format(args[0]))

        #Temporary hack to get create branch into source
        #TODO: git functions should probably all user parseargs, like git push
        if len(args) == 2:
            if args[0] == '-b':
                #TODO: Add tracking as a parameter
                print "Creating branch {0}".format(args[1])
                repo.create_branch(repo.active_branch, args[1], tracking=None)
                #Recursive call to checkout the branch we just created
                git_checkout([args[1]])
    else:
        print command_help['checkout']
        
def git_help(args):
    print 'help:'
    for key, value in command_help.items():
        print value
            
#Urllib2 opener for dulwich
def auth_urllib2_opener(config, top_level_url, username, password):
    if config is not None:
        proxy_server = config.get("http", "proxy")
    else:
        proxy_server = None

    # create a password manager
        password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()

        # Add the username and password.
        # If we knew the realm, we could use it instead of None.
        #top_level_url = "http://example.com/foo/"
        password_mgr.add_password(None, top_level_url, username, password)

        handler = urllib2.HTTPBasicAuthHandler(password_mgr)

    handlers = [handler]
    if proxy_server is not None:
        handlers.append(urllib2.ProxyHandler({"http": proxy_server}))
    opener = urllib2.build_opener(*handlers)
    if config is not None:
        user_agent = config.get("http", "useragent")
    else:
        user_agent = None
    if user_agent is None:
        user_agent = default_user_agent_string()
    opener.addheaders = [('User-agent', user_agent)]
    return opener

commands = {
    'init': git_init
    ,'add': git_add
    ,'rm': git_rm
    ,'commit': git_commit
    ,'clone': git_clone
    ,'modified': git_modified 
    ,'log': git_log
    ,'push': git_push
    ,'pull': git_pull
    ,'fetch': git_fetch
    ,'branch': git_branch
    ,'checkout': git_checkout
    ,'remote': git_remote
    ,'reset': git_reset
    ,'status': git_status
    ,'help': git_help
    }
if __name__=='__main__':
    if len(sys.argv)==1:
        sys.argv=sys.argv+['-h']

    ap = argparse.ArgumentParser()
    subparser=ap.add_subparsers()
    for key,value in commands.iteritems():
        sp=subparser.add_parser(key, help=command_help[key] ,add_help=False)
        sp.set_defaults(func=commands[key])
    ns,args=ap.parse_known_args()
    ns.func(args)
   # ap.add_argument('command',action='store',default='help',choices=command_help.keys(),nargs='?')
    
   # ns,args = ap.parse_known_args()
    #strargs=[str(a) for a in args]
    #func=commands[ns.command](strargs)
