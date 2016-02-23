# coding: utf-8
'''
Usage: gh <command> [<args>...]

supported commands are:
	gh fork <repo>		forks user/repo
	gh create <repo>	 [<args>...]		creates a nee repo
	gh pull <base> <head>	pull request into base (user/repo:branch) from head(user:branch)
'''
def install_module_from_github(username, package_name, folder, version):
    """
    Install python module from github zip files
    """
    cmd_string = """
        echo Installing {1} {3} ...
        wget https://github.com/{0}/{1}/archive/{3}.zip -o $TMPDIR/{1}.zip
        mkdir $TMPDIR/{1}_src
        unzip $TMPDIR/{1}.zip -d $TMPDIR/{1}_src
        rm -f $TMPDIR/{1}.zip
        mv $TMPDIR/{1}_src/{2} $STASH_ROOT/lib/
        rm -rf $TMPDIR/{1}_src
        echo Done
        """.format(username,
                   package_name,folder,
                   version
                   )
    globals()['_stash'](cmd_string)


try:
    import github
except ImportError:
    install_module_from_github('pygithub', 'pygithub', 'github','master')
    import github

try: 
	import docopt
except  ImportError:
	install_module_from_github('docopt','docopt','docopt.py','master')
from docopt import docopt
from github import Github
import keychain,console

class GitHubRepoNotFoundError(Exception):
	pass


def gh_fork( argv):
	'''Usage: gh fork REPO

			Fork a repo to your own github account.
			REPO	-  repo name of form user/repo
			
	'''
	args=docopt(gh_fork.__doc__, argv=argv)
	console.show_activity()
	g,user = setup_gh()
	try:
		other_repo = g.get_repo(args['REPO'])
		if other_repo:
			mine=user.create_fork(other_repo)
			print 'fork created:', mine.url
		else:
			pass
	finally:
		console.hide_activity()
		
def gh_create(argv):
	'''Usage: gh create [options] NAME 

	Options:
	-s <desc>, --description <desc>		Repo description
	-h <url>, --homepage <url>				Homepage url
	-p, --private		private
	-i, --has_issues		has issues
	-w, --has_wiki			has wiki
	-d, --has_downloads		has downloads
	-a, --auto_init		create readme and first commit
	-g <ign>, --gitignore_template <ign>  create gitignore using string
	
	
	'''

	args=docopt(gh_create.__doc__, argv=argv)
	print args
	kwargs= {key[2:]:value for key,value in args.items() if key.startswith('--') and key != '--private' and value}
	print kwargs
	console.show_activity()
	try:
		g,user = setup_gh()
		r=user.create_repo(args['NAME'],**kwargs)
		print 'Created %s'%r.c
	finally:
		console.hide_activity()
def setup_gh():
	keychainservice='stash.git.github.com'
	user = dict(keychain.get_services())[keychainservice]
	pw = keychain.get_password(keychainservice, user)
	g=Github(user,pw)
	u=g.get_user()
	return g, u

if __name__=='__main__':
	args=docopt(__doc__, version='0.1', options_first=True)
	cmd=args['<command>']
	argv=[cmd]+args['<args>']
	try:
		globals()['gh_%s'%cmd](argv)
	except KeyError:
		print 'no such cmd'
		raise