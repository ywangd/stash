'''
Distributed version control system

Commands:
    init:  git init <directory> - initialize a new Git repository
    add: git add <file1> .. [file2] .. - stage one or more files
    rm: git rm <file1> .. [file2] .. - unstage one or more files
    commit: git commit <message> <name> <email> - commit staged files
    merge:  git merge [--abort] [--msg <msg>] [<commit>]  merge another commit into HEAD
    clone: git clone <url> [path] - clone a remote repository
    modified: git modified - show what files have been modified
    log: git log - Options:\n\t[-l|--length  numner_of _results]\n\t[--oneline Print commits in a concise {commit} {message} form]\n\t[-f|--format format string can use {message}{author}{author_email}{committer}{committer_email}{merge}{commit}]\n\t[-o|--output]  file_name
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

SAVE_PASSWORDS = True

import argparse
import urlparse,urllib2,keychain
import sys,os,posix
import editor #for reloading current file
# temporary -- install required modules

#needed for dulwich: subprocess needs to have Popen
import subprocess
if not hasattr(subprocess,'call'):
	def Popen(*args,**kwargs):
		pass
	def call(*args,**kwargs):
		return 0
	subprocess.Popen=Popen
	subprocess.call=call
GITTLE_URL='https://github.com/jsbain/gittle/archive/master.zip'
FUNKY_URL='https://github.com/FriendCode/funky/archive/master.zip'
DULWICH_URL='https://github.com/jsbain/dulwich/archive/ForStaSH_0.12.2.zip'
REQUIRED_DULWICH_VERSION = (0,12,2)
AUTODOWNLOAD_DEPENDENCIES = True 

if AUTODOWNLOAD_DEPENDENCIES:
    libpath=os.path.join(os.environ['STASH_ROOT'] ,'lib')
    if not libpath in sys.path:
        sys.path.insert(1,libpath)
    download_dulwich = False 
    
    #DULWICH
    try:  
        import dulwich
        from dulwich.client import default_user_agent_string
        from dulwich import porcelain
        from dulwich.index import index_entry_from_stat
        if not dulwich.__version__ ==  REQUIRED_DULWICH_VERSION:
            print 'Dulwich version was {}.  Required is {}.  Attempting to reload'.format(dulwich.__version__,REQUIRED_DULWICH_VERSION)
            for m in [m for m in sys.modules if m.startswith('dulwich')]:
                del sys.modules[m]
            import dulwich
            from dulwich.client import default_user_agent_string
            from dulwich import porcelain
            from dulwich.index import index_entry_from_stat
            if not dulwich.__version__ ==  REQUIRED_DULWICH_VERSION:
                print 'Could not find correct version. Will download proper fork now'
                download_dulwich = True
            else:
                print 'Correct version loaded.'
    except ImportError as e:
        print 'dulwich was not found.  Will attempt to download. '
        download_dulwich = True 
    try:
        if download_dulwich:
            if not raw_input('Need to download dulwich.  OK to download [y/n]?') == 'y':
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
                reload(dulwich)
            except NameError:
                pass 
            #try the imports again
            import dulwich
            from dulwich.client import default_user_agent_string
            from dulwich import porcelain
            from dulwich.index import index_entry_from_stat
    except Exception:
        print '''Still could not import dulwich.
            Perhaps your network connection was unavailable.
            You might also try deleting any existing dulwich versions in site-packages or elsewhere, then restarting pythonista.'''

    #gittle, funky
    # todo... check gittle version
    try:
        gittle_path=os.path.join(libpath,'gittle')
        funky_path=os.path.join(libpath,'funky')
        #i have no idea why this is getting cleared...
        if libpath not in sys.path:
           sys.path.insert(1,libpath)
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
    import dulwich
    from dulwich.client import default_user_agent_string
    from dulwich import porcelain
    from dulwich.index import index_entry_from_stat
    from gittle import Gittle

dulwich.client.get_ssh_vendor = dulwich.client.ParamikoSSHVendor
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
    , 'merge': 'git merge <merge_commit> - merge another branch or commit and head into current working tree.   see git merge -h'
    ,'checkout': 'git checkout <branch> - check out a particular branch in the Git tree'
    ,'branch': 'git branch - show and manage branches.  see git branch -h'
    ,'remote': 'git remote [remotename remoteuri] list or add remote repos '
    ,'status': 'git status - show status of files (staged unstaged untracked)'
    ,'reset': 'git reset [<commit>] <paths>  reset <paths> in staging area back to their state at <commit>.  this does not affect files in the working area.  \ngit reset [ --mixed | --hard ] [<commit>] reset a repo to its pre-change state. default resets index, but not working tree.  i.e unstages all files.   --hard is dangerous, overwriting index and working tree to <commit>'
    , 'diff': 'git diff  show changed files in staging area'
    ,'help': 'git help'
          }


    
#Find a git repo dir
def _find_repo(path):
    try:
        subdirs = os.walk(path).next()[1]
    except StopIteration: # happens if path is not listable
        return None
        
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
    repo_dir = _find_repo(os.getcwd())
    if not repo_dir:
        raise Exception("Current directory isn't a git repository")
    return Gittle(repo_dir)

def _confirm_dangerous():
        repo = _get_repo()
        status=porcelain.status(repo.path)
        if any(status.staged.values()+status.unstaged):
            force=raw_input('WARNING: there are uncommitted modified files and/or staged changes. These could be overwritten by this command. Continue anyway? [y/n] ')
            if not force=='y':
                raise Exception('User cancelled dangerous operation')
                
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
        status = porcelain.status(repo.repo.path)
        print 'STAGED'
        for k,v in status.staged.iteritems():
            if v:
                print k,v
        print 'UNSTAGED LOCAL MODS'
        print status.unstaged
        
    else:
        print command_help['status']

def git_remote(args):
    '''List remote repos'''
    if len(args) == 0:
        repo = _get_repo()
        for key, value in repo.remotes.items():
            print '{} {}'.format(key, value)
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
            
            if os.path.exists(os.path.join(repo.repo.path, file)):
                print 'Adding {0}'.format(file)
                porcelain.add(repo.repo.path, [file])
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
            porcelain.rm(repo.repo.path, args)

    else:
        print command_help['rm']
def launch_subcmd(cmd,args):
    cmdpath=os.path.join(os.environ['STASH_ROOT'],'lib','git',cmd)

    _stash(cmdpath + ' ' + ' '.join(args))
            
def git_branch(args):
    launch_subcmd('git-branch.py',args)
    
def git_merge(args):
    launch_subcmd('git-merge.py',args)

def git_reset(args):
    import git.gitutils as gitutils
    ap=argparse.ArgumentParser('reset')
    ap.add_argument('commit',nargs='?',action='store',default='HEAD')
    ap.add_argument('paths',nargs='*')
    mode=ap.add_mutually_exclusive_group()
    mode.add_argument('--hard',action='store_true')
    mode.add_argument('--mixed',action='store_true')
    mode.add_argument('--soft',action='store_true')
 
    ap.add_argument('--merge',action='store_true')
    ns=ap.parse_args(args)

        
    repo = _get_repo()
    
    if ns.merge:
        try:
            os.remove(os.path.join(repo.repo.controldir(),'MERGE_HEAD'))
            os.remove(os.path.join(repo.repo.controldir(),'MERGE_MSG'))
        except OSError:
            pass  #todo, just no such file
        
    #handle optionals
    commit= ns.commit
    # first arg was really a file
    paths=ns.paths or []
    if not commit in repo and os.path.exists(commit): #really specified a path
        paths=[commit]+paths
        commit = None
    elif not commit in repo and not commit in repo.branches and not commit in repo.remote_branches and not os.path.exists(commit):
        raise Exception('{} is not a valid commit or file'.format(commit))
    if not commit:
        commit='HEAD'
    
    if not paths:
        #reset HEAD, if commit in branches
        if commit == 'HEAD':
            commit = repo.head
        elif commit in repo.branches:
            print 'updating HEAD to ', commit
            repo.repo.refs.set_symbolic_ref('HEAD',repo._format_ref_branch(commit))
        else:
            print commit, 'is not a valid branchname.  head was not updated'
    if ns.hard:
        _confirm_dangerous()
 
    if ns.hard or ns.mixed:
    # first, unstage index
        if paths:
            unstage(commit,paths)
        else:
            print 'resetting index. please wait'
            unstage_all(commit)
            print 'complete'
 
    # next, rebuild files
    if ns.hard:
        treeobj=repo[repo[commit].tree]
        
        for path in paths:
            print 'resetting '+path
            relpath=repo.relpath(path)
            file_contents=repo[treeobj.lookup_path(repo.__getitem__,relpath)[1]].as_raw_string()
            with open(str(path),'w') as f:
                f.write(file_contents)

def get_config_or_prompt(repo, section, name, prompt, save=None):
    config = repo.repo.get_config()
    try:
        value = config.get(section, name)
    except KeyError:
        value = raw_input(prompt)
        if save == None:
            reply = raw_input('Save this setting? [y/n]')
            save = reply == 'y'
        if save:
            config.set(section, name, value)
            config.write_to_path()
    return value
        
def git_commit(args):
    ap=argparse.ArgumentParser('Commit current working tree.')
    ap.add_argument('message',default=None,nargs='?')
    ap.add_argument('name',default=None,nargs='?')
    ap.add_argument('email',default=None,nargs='?')
    ns=ap.parse_args(args)
    
    repo = _get_repo()
    merging = repo.repo.get_named_file('MERGE_HEAD')
    merge_head=None
    if merging:
        print 'merging in process:' 
        merge_head= merging.read() or ''
        merge_msg= repo.repo.get_named_file('MERGE_MSG').read() or ''
        print merge_msg
        ns.message = ns.message or '' + merge_msg
    if not ns.message:
        ns.message=raw_input('Commit Message: ')

    ns.name = ns.name or get_config_or_prompt(repo, 'user', 'name', 'Author Name: ')
    ns.email = ns.email or get_config_or_prompt(repo, 'user', 'email', 'Author Email: ')
         
    try:
    
        author = "{0} <{1}>".format(ns.name, ns.email)

        print repo.repo.do_commit(message=ns.message
                                  , author=author
                                  , committer=author 
                                  , merge_heads=[merge_head] if merge_head else None)
        if merging:
            try:
                os.remove(os.path.join(repo.repo.controldir(),'MERGE_HEAD'))
                os.remove(os.path.join(repo.repo.controldir(),'MERGE_MSG'))
            except OSError:
                pass  #todo, just no such file
    except:
        print 'commit Error: {0}'.format(sys.exc_value)

    

def git_clone(args):
    if len(args) > 0:
           url = args[0]
           repo = Gittle.clone(args[0], args[1] if len(args)>1 else os.path.split(args[0])[-1].rstrip('.git'), bare=False)

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
    if not urlparse.urlparse(result.url).scheme:
        raise Exception('url must match a remote name, or must start with http:// or https://')
    print 'Starting fetch, this could take a while'
    remote_refs=porcelain.fetch(repo.repo.path,result.url)
    print 'Fetch successful.  Importing refs'
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
    print 'Checking for deleted remote refs'
    #delete unused remote refs
    for k in gittle.utils.git.subrefs(repo.refs,heads_base):
        if k not in clean_remote_heads:
            print 'Deleting {}'.format('/'.join([heads_base,k]))
            del repo.refs['/'.join([heads_base,k])]
    print 'Fetch complete'

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
    if not user and SAVE_PASSWORDS and result.url.startswith('http'):
        try:
            user = dict(keychain.get_services())[keychainservice]
        except KeyError:
            user = raw_input('Enter username: ')
            pw = raw_input('Enter password: ')
            #user, pw = console.login_alert('Enter credentials for {0}'.format(netloc))

    outstream = StringIO()
    if user:
        if not pw and SAVE_PASSWORDS:
            pw = keychain.get_password(keychainservice, user)

        #Check again, did we retrieve a password?
        if not pw:
            user, pw = console.login_alert('Enter credentials for {0}'.format(netloc), login=user)
        host_with_auth='{}:{}@{}'.format(user,pw,netloc)
        url=urlparse.urlunparse(
            urlparse.urlparse(result.url)._replace(
                netloc=host_with_auth))
        porcelain.push(repo.repo.path, url, branch_name, errstream=outstream)
        keychain.set_password(keychainservice, user, pw)

    else:
        porcelain.push(repo.repo.path, result.url, branch_name, errstream=outstream)
 
    for line in outstream.getvalue().split('\n'):
            print(line.replace(pw, '*******'))
    
    print 'success!'

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

    parser.add_argument('--oneline',
                        action='store_true',
                        dest='oneline',
                        default=False)
                        
    results = parser.parse_args(args)

    try:
        repo = _get_repo()
        outstream = StringIO()
        porcelain.log(repo.repo.path, max_entries=results.max_entries,outstream=outstream)
        
        if not results.oneline:
            print outstream.getvalue()
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
        print command_help['log']

def git_diff(args):
    '''prints diff of currently staged files to console.. '''
    repo=_get_repo()

    index=repo.repo.open_index()
    store=repo.repo.object_store
    index_sha=index.commit(store)
    #tree_ver=store[tree.lookup_path(store.peel_sha,file)[1]].data
    porcelain.diff_tree('.',repo[repo['HEAD'].tree].id,repo[index_sha].id, sys.stdout)


def git_checkout(args):

    if len(args) in [1,2]:
        repo = _get_repo()
        _confirm_dangerous()
        if os.path.exists(os.path.join(repo.repo.controldir(),'MERGE_HEAD')) :
            #just cancel in progress merge
            os.remove(os.path.join(repo.repo.controldir(),'MERGE_HEAD'))
            os.remove(os.path.join(repo.repo.controldir(),'MERGE_MSG'))
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
            refresh_editor()
    else:
        print command_help['checkout']
        
def refresh_editor():
    #reload current file in editor
    # TODO: only reload if the file was recently updated...
    try:
        sel=editor.get_selection()
        editor.open_file(editor.get_path())
        import time
        time.sleep(0.5) #let the file load
        editor.replace_text(sel[0],sel[0],'') #force scroll
        editor.set_selection(sel[0],sel[1])
    except:
        print 'Could not refresh editor.  continuing anyway'
    
def git_help(args):
    print 'help:'
    for key, value in command_help.items():
        print value
            
           


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
    ,'merge': git_merge
    ,'checkout': git_checkout
    ,'remote': git_remote
    ,'reset': git_reset
    ,'status': git_status
    ,'diff': git_diff
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
