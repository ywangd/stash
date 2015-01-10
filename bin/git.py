
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
    pull: git pull [http(s)://<remote repo>] - pull changes from a remote repository
    checkout: git checkout <branch> - check out a particular branch in the Git tree
    branch: git branch - show branches
    remote: git remote - list remote repos 
    status: git status - show status of files (staged unstaged untracked)
    reset: git reset - reset a repo to its pre-change state
    help: git help
'''

SAVE_PASSWORDS = True


# temporary -- install required modules

GITTLE_URL='https://github.com/jsbain/gittle/archive/master.zip'
FUNKY_URL='https://github.com/FriendCode/funky/archive/master.zip'
DULWICH_URL='https://github.com/transistor1/dulwich/archive/master.zip'

if True:
    libpath=os.path.join(_stash.runtime.envars['STASH_ROOT'] ,'lib')
    if not libpath in sys.path:
        sys.path.insert(1,libpath)
    try:  
        from dulwich.client import default_user_agent_string
        from dulwich import porcelain
    
    except ImportError:
        _stash('wget {} -o $TMPDIR/dulwich.zip'.format(DULWICH_URL))
        _stash('unzip $TMPDIR/dulwich.zip -d $TMPDIR/dulwich')
        _stash('mv $TMPDIR/dulwich/dulwich $STASH_ROOT/lib/')
        _stash('rm  $TMPDIR/dulwich.zip')
        _stash('rm -r $TMPDIR/dulwich')
    
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
    from gittle import Gittle

import argparse
import getpass
import urlparse
import sys,os



command_help={    'init':  'initialize a new Git repository'
    ,'add': 'stage one or more files'
    ,'rm': 'git rm <file1> .. [file2] .. - unstage one or more files'
    ,'commit': 'git commit <message> <name> <email> - commit staged files'
    ,'clone': 'git clone <url> [path] - clone a remote repository'
    ,'modified': 'git modified - show what files have been modified'
    ,'log': 'git log - Options:\n\t[-l|--length  numner_of _results]\n\t[-f|--format format string can use {message}{author}{author_email}{committer}{committer_email}{merge}{commit}]\n\t[-o|--output]  file_name'
    ,'push': 'git push [http(s)://<remote repo>] [-u username[:password]] - push changes back to remote'
    ,'pull': 'git pull [http(s)://<remote repo>] - pull changes from a remote repository'
    ,'checkout': 'git checkout <branch> - check out a particular branch in the Git tree'
    ,'branch': 'git branch - show branches'
    ,'remote': 'git remote - list remote repos '
    ,'status': 'git status - show status of files (staged unstaged untracked)'
    ,'reset': 'git reset - reset a repo to its pre-change state'
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
    else:
        print command_help['remote']

def git_add(args):
    if len(args) > 0:
        repo = _get_repo()
        cwd = os.getcwd()
        print 'cwd:',cwd
        print 'repo',repo.path
        args = [os.path.join(os.path.relpath(cwd, repo.path), x)
                    if not os.path.samefile(cwd, repo.path) else x for x in args]
        for file in args:
            print 'Adding {0}'.format(file)
            porcelain.add(repo.repo, [file])
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

def git_branch(args):
    if len(args) == 0:
        repo = _get_repo()
        active = repo.active_branch
        for key, value in repo.branches.items():
            print ('* ' if key == active else '') + key, value
    else:
        print command_help['branch']

def git_reset(args):
    if len(args) == 0:
        repo = _get_repo()
        porcelain.reset(repo.repo, 'hard')
    else:
        print command_help['reset']

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
        url = args[0] if len(args)==1 else repo.remotes.get('origin','')
        if url:
            repo.pull(origin_uri=url)
        else:
            print 'No pull URL.'
    else:
        print command_help['git pull']



def git_push(args):
    parser = argparse.ArgumentParser(prog='git push'
                                     , usage='git push [http(s)://<remote repo>] [-u username[:password]]'
                                     , description="Push to a remote repository")
    parser.add_argument('url', type=str, nargs='?', help='URL to push to')
    parser.add_argument('-u', metavar='username[:password]', type=str, required=False, help='username[:password]')
    result = parser.parse_args(args)

    user, sep, pw = result.u.partition(':') if result.u else (None,None,None)

    repo = _get_repo()

    #Try to get the remote origin
    if not result.url:
        result.url = repo.remotes.get('origin','')

    branch_name = os.path.join('refs','heads', repo.active_branch)  #'refs/heads/%s' % repo.active_branch

    print "Attempting to push to: {0}, branch: {1}".format(result.url, branch_name)

    netloc = urlparse.urlparse(result.url).netloc

    keychainservice = 'shellista.git.{0}'.format(netloc)

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
            user, pw = console.login_alert('Enter credentials for {0}'.format(netloc))

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
        if len(args) == 1:
            repo.clean_working()
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
    ,'branch': git_branch
    ,'checkout': git_checkout
    ,'remote': git_remote
    ,'reset': git_reset
    ,'status': git_status
    ,'help': git_help
    }
if __name__=='__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('command',action='store',default='help',choices=command_help.keys(),nargs='?')
    ns,args = ap.parse_known_args()
    func=commands[ns.command](args)
