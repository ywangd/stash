# A package manager meant for Pythonista, built on StaSh.

import requests
import sys
import argparse
from os import remove, mkdir, rename, listdir, getcwd
from shutil import rmtree

cwd = getcwd()
documentsIndex = cwd.index("Documents")
documentsIndex += len("Documents")
ROOT = cwd[:documentsIndex]

class stansi: # Collection of Stash's ANSI escape codes.
	bold = u"\x9b1m"
	underscore = u"\x9b4m"
	attr_end = u"\x9b0m"
	
	fore_red = u"\x9b31m"
	fore_green = u"\x9b32m"
	fore_brown = u"\x9b33m"
	fore_blue = u"\x9b34m"
	fore_pink = u"\x9b35m"
	fore_cyan = u"\x9b36m"
	fore_white = u"\x9b37m"
	fore_end = u"\x9b39m"
	
	back_red = u"\x9b41m"
	back_green = u"\x9b42m"
	back_brown = u"\x9b43m"
	back_blue = u"\x9b44m"
	back_pink = u"\x9b45m"
	back_cyan = u"\x9b46m"
	back_white = u"\x9b47m"
	back_end = u"\x9b49m"
	
def Red(text):
	return stansi.fore_red+text+stansi.fore_end
def Blue(text):
	return stansi.fore_blue+text+stansi.fore_end
def Green(text):
	return stansi.fore_green+text+stansi.fore_end
def Cyan(text):
	return stansi.fore_cyan+text+stansi.fore_end
		
class SWConfig (object): # Parser for the config files such as the repository listing.
	def __init__(self, content):
		self.data = {}
		for line in content.splitlines():
			key = line.split("=")[0]
			value = line.split("=")[1]
			self.data[key] = value
			
	def __getitem__(self, key):
		return self.data[key]
		
	def keys(self):
		return self.data.keys()
		
def download_package(url, package_name): # Handles the installation of packages directories (since they're no longer tarfiles)
	content_listing = ["bin.py", "meta.latte"]
	mkdir(ROOT+"/"+package_name)
	for item in content_listing:
		requested = requests.get(url+"/"+package_name+"/"+item)
		content = requested.text
		requested.close()
		if content == "404: Not Found\n":
			print(Red("ERROR") + ": Package not found.")
			sys.exit()
		opened = open(ROOT+"/"+package_name+"/"+item, "w")
		opened.write(content)
		opened.close()

def main(sargs):
	parser = argparse.ArgumentParser()
	parser.add_argument("method", help="What action to perform (install, remove, etc)", type=str)
	parser.add_argument("package", help="Name of package", type=str)
	args = parser.parse_args(sargs)
	
	try:
		opened = open(".latte-repos.swconf", "r")
		opened.close()
	except:
		opened = open(".latte-repos.swconf", "w")
		print(Red("WARNING") + ": Repository listing doesn't exist, rebuilding to default...")
		opened.write("universe=https://raw.githubusercontent.com/Seanld/latte-universe/master")
		opened.close()
	
	repo_listing_opened = open(".latte-repos.swconf", "r")
	listing_content = repo_listing_opened.read()
	repo_listing_opened.close()
	REPOSITORIES = SWConfig(listing_content)
		
	if args.method == "install":
		packageSplitted = args.package.split("/")
		try:
			package_name = packageSplitted[1]
			repo_to_use = REPOSITORIES[packageSplitted[0]]
		except IndexError:
			
			repo_to_use = REPOSITORIES["universe"]
			package_name = packageSplitted[0]
		print(Red("WARNING") + ": No repository specified, using universe by default...")
		try:
			download_package(repo_to_use, package_name)
		except:
			stoutput("ERROR", "Couldn't find package", "error")
			sys.exit()
		# Move to correct locations
		print("Installing")
		try:
			rename(ROOT+"/"+package_name+"/meta.latte", ROOT+"/stash_extensions/latte/"+package_name+".latte")
		except:
			mkdir(ROOT+"/stash_extensions/latte")
			rename(ROOT+"/"+package_name+"/meta.latte", ROOT+"/stash_extensions/latte/"+package_name+".latte")
		rename(ROOT+"/"+package_name+"/bin.py", ROOT+"/stash_extensions/bin/"+package_name+".py")
		rmtree(ROOT+"/"+package_name)
		print(Green("SUCCESS") + ": Package '"+package_name+"' successfully installed!")
	elif args.method == "remove":
		try:
			remove(ROOT+"/stash_extensions/bin/"+args.package+".py")
			remove(ROOT+"/stash_extensions/latte/"+args.package+".latte")
		except:
			print(Red("ERROR") + ": Couldn't remove package; not found in resources.")
			sys.exit()
		print(Green("SUCCESS") + ": '"+args.package+"' removed!")
	elif args.method == "update":
		print("Jeez! Sorry, but we are currently working on self-update capabilities. For now, just redo the install process to update.")
	elif args.method == "new":
		try:
			mkdir(args.package)
			config = open(args.package+"/meta.latte", "w")
			config.write("developer=Your name here\ndescription=Enter description of your app here\nversion=0.1")
			config.close()
			index = open(args.package+"/bin.py", "w")
			index.write("# This is just an example template. You can change this all you like.\n\nimport sys\nimport argparse\n\ndef main(sargs):\n\tparser = argparse.ArgumentParser()\n\tparser.add_argument('echo', help='What you want the command to echo back.')\n\targs = parser.parse_args(sargs)\n\t\n\tprint('Echoing back: '+args.echo)\n\nif __name__ == '__main__':\n\tmain(sys.argv[1:])")
			index.close()
			print(Green("SUCCESS") + ": Package '"+args.package+"' generated, check current working directory!")
		except:
			print(Red("ERROR") + ": Couldn't generate package; directory may already exist.")
	elif args.method == "add-repo":
		try:
			request = requests.get(args.package+"/init.latte")
			data = request.text
			request.close()
			data_org = SWConfig(data)
			nickname = data_org["NICKNAME"]
			repo_listing = open(".latte-repos.swconf", "a")
			repo_listing.write("\n"+nickname+"="+args.package)
			repo_listing.close()
			print(Green("SUCCESS") + ": '"+nickname+"' added to repositories!")
		except:
			print(Red("ERROR") + ": Either repository doesn't exist, or does not contain an 'init.latte' file.")
	elif args.method == "list-repos":
		if args.package == "all":
			opened = open(".latte-repos.swconf")
			content = opened.read()
			opened.close()
			as_config = SWConfig(content)
			for repo in as_config.keys():
				print(Cyan(repo) + ": " + Green(as_config[repo]))
	else:
		print(Red("ERROR") + ": Unknown command '"+args.method+"'!")

if __name__ == "__main__":
	main(sys.argv[1:])
