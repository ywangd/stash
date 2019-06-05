# coding: utf-8
'''
Usage: gh <command> [<args>...]
       gh <command> (-h|--help)
supported commands are:
	gh fork <repo>		forks user/repo
	gh create <repo>		creates a new repo
	gh pull <repo> <base> <head>	  create a pull request
	gh list_keys	list user keys
	gh create_key <title> [<public_key_path>] add a key to github (or create new key if none exist)
For all commands, use gh <command> --help for more detailed help

NOTE: assumes a keychain user/pass stored in 	keychainservice='stash.git.github.com', which is also the default from the git module.
'''
from __future__ import print_function
import inspect
import console
import keychain
from github import Github
from docopt import docopt
import os
import sys
from functools import wraps

from six.moves import input


_stash = globals()["_stash"]


try:
    import github
except ImportError:
    print("Could not import 'github', installing it...")
    _stash("pip install pygithub")
    import github
try:
    import docopt
except ImportError:
    print("Could not import 'docopt', installing it...")
    _stash("pip install docopt")


class GitHubRepoNotFoundError(Exception):
    pass


def command(func):
    @wraps(func)
    def tmp(argv):
        if len(argv) == 1:
            if func.__name__ not in ['gh_list_keys']:
                argv.append('--help')
        try:
            args = docopt(func.__doc__, argv=argv)
            return func(args)
        except SystemExit as e:
            print(e)

    return tmp


@command
def gh_fork(args):
    '''Usage: gh fork <repo>

                    Fork a repo to your own github account.
                    <repo>	-  repo name of form user/repo

    '''
    console.show_activity()
    g, user = setup_gh()
    try:
        other_repo = g.get_repo(args['<repo>'])
        if other_repo:
            mine = user.create_fork(other_repo)
            print('fork created: {}/{}'.format(mine.owner.login, mine.name))
        else:
            pass
    finally:
        console.hide_activity()


@command
def gh_create(args):
    '''Usage: gh create [options] <name>

    Options:
    -h, --help             This message
    -s <desc>, --description <desc>		Repo description
    -h <url>, --homepage <url>				Homepage url
    -p, --private          private
    -i, --has_issues       has issues
    -w, --has_wiki  			 has wiki
    -d, --has_downloads    has downloads
    -a, --auto_init     		create readme and first commit
    -g <ign>, --gitignore_template <ign>  create gitignore using string


    '''
    kwargs = {key[2:]: value for key,
              value in args.items() if key.startswith('--') and value}
    console.show_activity()
    try:
        g, user = setup_gh()
        r = user.create_repo(args['<name>'], **kwargs)
        print ('Created %s' % r.html_url)
    finally:
        console.hide_activity()


def parse_branch(userinput):
    if ':' in userinput:
        owner, branch = userinput.split(':')
    else:
        owner = userinput
        branch = 'master'
    return owner, branch


def parent_owner(user, reponame):
    return user.get_repo(reponame).parent.owner.login


@command
def gh_pull(args):
    '''Usage:
    gh pull <reponame> <base> [<head>]
    gh pull <reponame> <base> [<head>] --title <title> [--body <body>]
    gh pull <reponame> <base> [<head>] -i <issue>

Options:
    -h, --help   							This message
    -t <title>, --title <title>  	Title of pull request
    -b <body>, --body <body>  		Body of pull request [default: ]
    -i <issue>, --issue <issue>  	Issue number
Examples:
    gh pull stash ywangd jsbain
    gh pull stash ywangd:dev jsbain:dev
    gh pull stash :dev :master

    base and head should be in the format owner:branch.
    if base owner is omitted, owner of parent repo is used.
    if head owner is omitted, user is used
    '''

    console.show_activity()
    try:
        g, user = setup_gh()
        reponame = args['<reponame>']
        baseowner, basebranch = parse_branch(args['<base>'])
        if not baseowner:
            baseowner = parent_owner(reponame)
        if not args['<head>']:
            args['<head>'] = ':'
        headowner, headbranch = parse_branch(args['<head>'])
        if not headowner:
            headowner = user.login

        baserepo = g.get_user(baseowner).get_repo(reponame)

        kwargs = {}
        if args['--issue']:
            kwargs['issue'] = baserepo.get_issue(args['--issue'])
        elif not args['--title']:
            kwargs['title'] = input('Enter pull title:')
            kwargs['body'] = input('Enter pull body:')
        else:
            kwargs['title'] = args['--title']
            kwargs['body'] = args['--body'] or ''

        kwargs['base'] = basebranch
        kwargs['head'] = ':'.join([headowner, headbranch])
        pullreq = baserepo.create_pull(**kwargs)

        print ('Created pull %s' % pullreq.html_url)
        print ('Commits:')
        print([(x.sha, x.commit.message) for x in pullreq.get_commits()])
        print ('Changed Files:')
        print([x.filename for x in pullreq.get_files()])
    finally:
        console.hide_activity()
    print('success')


@command
def gh_list_keys(args):
    '''Usage:
            gh list_keys [options]
Options:
    -h, --help   							This message

List keys
    '''
    g, u = setup_gh()
    for key in u.get_keys():
        print('{}:\n {}\n'.format(key.title, key.key))


@command
def gh_create_key(args):
    '''Usage:
    gh create_key <title> [<public_key_path>]

Options:
    -h, --help   							This message

Examples:
    gh create_key ipad ~/.ssh/id_rsa.pub
    gh create_key ipad    (checks for ~/.ssh/id_rsa.pub, or creates new key if needed using ssh-keygen )
    '''
    title = args['<title>']
    default_keyfile = os.path.expanduser('~/.ssh/id_rsa.pub')
    if not args['<public_key_path>']:
        if not os.path.exists(default_keyfile):
            print('Creating a ssh key in ~/.ssh/')
            cmd_string = '''
			echo ssh-keygen -d rsa -b2048
			ssh-keygen -trsa -b2048
			'''
            _stash(cmd_string)
        args['<public_key_path>'] = default_keyfile
    # if private key, use pub key
    if not args['<public_key_path>'].endswith('.pub'):
        args['<public_key_path>'] += '.pub'
    if not os.path.exists(args['<public_key_path>']):
        raise Exception('Public Key file not found!')
    g, u = setup_gh()
    with open(args['<public_key_path>']) as pubkey:
        u.create_key(title, pubkey.read())


def setup_gh():
    keychainservice = 'stash.git.github.com'
    user = dict(keychain.get_services())[keychainservice]
    pw = keychain.get_password(keychainservice, user)
    g = Github(user, pw)
    u = g.get_user()

    return g, u


if __name__ == '__main__':
    import sys
    if len(sys.argv) == 1:
        sys.argv.append('--help')

    args = docopt(__doc__, version='0.1', options_first=True)
    cmd = args['<command>']
    argv = [cmd] + args['<args>']
    try:
        func = locals()['gh_%s' % cmd]
    except KeyError:
        print ('No such cmd')
        print (__doc__)
        raise
    func(argv)
