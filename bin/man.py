"""Display help for a command in $STASH_ROOT/bin/ or a topic, or list all commands if no name is given.
"""

from __future__ import print_function

import argparse
import ast
import os
import sys

_stash = globals()["_stash"]

TYPE_CMD = "command"
TYPE_PAGE = "page"
TYPE_NOTFOUND = "not found"

BINPATH = os.path.join(os.environ["STASH_ROOT"], "bin")
PAGEPATH = os.path.join(os.environ["STASH_ROOT"], "man")

if not os.path.exists(PAGEPATH):
	os.mkdir(PAGEPATH)

def all_commands():
    cmds = [
        fn[:-3] for fn in os.listdir(BINPATH)
        if fn.endswith(".py")
        and not fn.startswith(".")
        and os.path.isfile(os.path.join(BINPATH, fn))
    ]
    cmds.sort()
    return cmds

def get_type(search):
	"""returns (type, path) for a given topic/command."""
	cmdpath = find_command(search)
	if cmdpath is not None:
		return (TYPE_CMD, cmdpath)
	if "(" in search and ")" in search:
		try:
			pn = int(search[search.index("(")+1:search.index(")")])
		except:
			print(_stash.text_color("Invalid Pagenumber", "red"))
			sys.exit(1)
		search = search[:search.index("(")]
	else:
		pn = 1
	if "." in search:
		to_search = search
		found = os.listdir(PAGEPATH)
	else:
		to_search = search#[:search.index(".")]
		found = [(fn[:fn.index(".")] if "." in fn else fn) for fn in os.listdir(PAGEPATH)]
	if to_search in found:
		ffns= [fn if fn.startswith(to_search+".") else None for fn in os.listdir(PAGEPATH)]
		ffn = filter(None, ffns)
		if len(ffn) == 0:
			#isdir
			pname = "page_" + str(pn)
			dirpath = os.path.join(PAGEPATH, to_search)
			for fn in os.listdir(dirpath):
				if fn.startswith(pname):
					fp = os.path.join(dirpath, fn)
					if not os.path.exists(fp):
						print(
							_stash.text_color("Page not found!", "red")
							)
					return (TYPE_PAGE, fp)
			return (TYPE_NOTFOUND, None)
		path = os.path.join(PAGEPATH, ffn[0])
		return (TYPE_PAGE, path)
	else:
		return (TYPE_NOTFOUND, None)
	

def find_command(cmd):
    if os.path.exists(BINPATH) and cmd + ".py" in os.listdir(BINPATH):
        return os.path.join(BINPATH, cmd + ".py")
    return None

def get_docstring(filename):
    with open(filename) as f:
        tree = ast.parse(f.read(), os.path.basename(filename))
    return ast.get_docstring(tree)

def get_summary(filename):
    docstring = get_docstring(filename)
    return docstring.splitlines()[0] if docstring else ''

def show_page(path):
	"""shows the page at path."""
	if not os.path.exists(path):
		print(
			_stash.text_color("Error: cannot find page!", "red"),
			)
		sys.exit(1)
	with open(path, "r") as fin:
		content = fin.read()
	if len(content.replace("\n","")) == 0:
		print(
			_stash.text_color("Error: help empty!", "red")
			)
		sys.exit(1)
	if path.endswith(".txt"):
		print(_stash.text_color("="*20,"yellow"))
		print(content)
		print("\n")
	elif path.endswith(".url"):
		print("opening webviewer...")
		_stash("webviewer -n '{u}'".format(u=content.replace("\n","")))
	elif path.endswith(".html"):
		print("opening quicklook...")
		_stash("quicklook {p}".format(p=path))
	else:
		print(_stash.text_color("="*20,"yellow"))
		print(content)
		print("\n")

def main(args):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("topic", nargs="?", help="the command/topic to get help for")
    ns = ap.parse_args(args)
    
    if not ns.topic:
        cmds = all_commands()
        if len(cmds) > 100:
            if raw_input("List all {} commands?".format(len(cmds))).strip().lower() not in ("y", "yes"):
                sys.exit(0)
        for cmd in cmds:
            print(_stash.text_bold('{:>11}: '.format(cmd)) + get_summary(find_command(cmd)))
        sys.exit(0)
    else:
        ft, path = get_type(ns.topic)
        
        if ft == TYPE_NOTFOUND:
            print(
            	_stash.text_color("man: no help for '{}'".format(ns.topic), "red")
            	)
            sys.exit(1)
        if ft == TYPE_CMD:
	        try:
	            docstring = get_docstring(path)
	        except Exception as err:
	            print(
	            	_stash.text_color("man: {}: {!s}".format(type(err).__name__, err), "red"),
	            	file=sys.stderr
	            	)
	            sys.exit(1)
	
	        if docstring:
	            print("Docstring of command '{}':\n{}".format(ns.topic, docstring))
	        else:
	            print(
	            	_stash.text_color("man: command '{}' has no docstring".format(ns.topic), "red")
	            	)
	        sys.exit(0)
        elif ft == TYPE_PAGE:
	      	show_page(path)
	      	sys.exit(0)

if __name__ == "__main__":
    main(sys.argv[1:])
