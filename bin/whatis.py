from __future__ import print_function
#by Siddharth Dushantha
#31 July 2017
from sys import argv
import json


file = '{"alias":"Define or print aliases","cat":"Print contents of file","cd":"Change current directory","clear":"Clear console","cp":"Copy file","crypt":"File encryption using AES in CBC mode","cowsay":"Generates ASCII picture of a cow with a message","curl":"Transfer from an URL","cut":"Cut out selection portions of each line of a file","du":"Summarize disk usage of the set of FILEs, recursively for directories","echo":"Output text to console","edit":"Open any text type files in Pythonista editor","find":"Powerful file searching tool","fg":"Bring a background job to foreground","ftpserver":"A simple FTP server","gci":"Interface to Pythons built-in garbage collector","git":"Git client","grep":"search contents of file(s)","head":"Display first lines of a file","httpserver":"A simple HTTP server with upload function","jobs":"List all jobs that are currently running","kill":"Terminate a running job","ls":"List files","mail":"Send emails with optional file attachment","man":"Show help message (docstring) of a given command","mc":"Easily work with multiple filesystems (e.g. local and FTP) synchronously","md5sum":"Print or check MD5 checksums","mkdir":"Create directory","monkeylord":"Manage monkey patches with the goal to make Pythonista more viable","mv":"Move file","openin":"Show the open in dialog to open a file in external apps","pbcopy":"Copy to iOS clipboard","pbpaste":"Paste from iOS clipboard","pip":"Search, download, install, update and uninstall pure Python packages from PyPI","printenv":"List environment variables","printhex":"Print hexadecimal dump of the given file","pwd":"Print current directory","python":"Run python scripts or modules","quicklook":"iOS quick look for files of known types","rm":"delete (remove) file","scp":"Copy files from/to remote servers","selfupdate":"Update StaSh from its GitHub repo","sha1sum":"Print of check SHA1 checksums","sha256sum":"Print of check SHA256 checksums","sort":"Sort a list, also see unique","source":"Evaluate a script in the current environment","ssh":"SSH client to either execute a command or spawn an interactive session on remote servers","ssh-keygen":"Generate RSA/DSA SSH Keys","stashconf":"Change StaSh configuration on the fly","tail":"Print last lines of a FILE","tar":"Manipulate archive files","touch":"Update timestamp of the given file or create it if not exist","uniq":"Remove duplicates from list, also see sort","unzip":"Unzip file","version":"Show StaSh installation and version information","wc":"Line, word, character counting","wget":"Get data from the net","whatis":"Search manual page databases","which":"Find the exact path to a command script","wol":"Wake on LAN using MAC address for launching a sleeping system","xargs":"Command constructing and executing utility","zip":"Zip file"}'
	
def main():
	data = json.loads(file)
	try:
		print(command+' - '+data[command])
	
	except KeyError:
		print('whatis: nothing appropriate')
	

command = argv[1]
main()
