# coding: utf-8
"""Opens the given URL in the webbrowser or an App."""
import argparse, webbrowser
import ui
from objc_util import on_main_thread

@on_main_thread
def open_url(url, modal=False):
	webbrowser.open(url, modal)

if __name__=="__main__":
	parser=argparse.ArgumentParser(description=__doc__)
	parser.add_argument("url", help="url to open", action="store")
	parser.add_argument("-m", "--modal", help="wait until the user closed the webbrowser", action="store_true", dest="modal")
	parser.add_argument("-n", "--insecure", help="prefix the url with http:// instead of https:// if no prefix is given", action="store_const", const="http://", default="https://", dest="prefix")
	ns=parser.parse_args()
	url=ns.url
	if not "://" in url:
		url=ns.prefix+url
	open_url(url,ns.modal)
