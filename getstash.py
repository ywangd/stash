import os
import urllib2
import random

URLBASE = 'https://raw.githubusercontent.com/ywangd/stash/master/'

FNAMES = ['stash.py', 'bin/selfupdate.sh', 'bin/echo.py', 'bin/wget.py', 'bin/unzip.py', 'bin/rm.py', 'bin/alias.py']

STASH_DIR = os.path.expanduser("~/Documents/stash")

if not os.path.exists(STASH_DIR):
    os.mkdir(STASH_DIR)

if not os.path.exists(os.path.join(STASH_DIR, 'bin')):
    os.mkdir(os.path.join(STASH_DIR, 'bin'))

if __name__ == "__main__":
    for fname in FNAMES:
        # Random number to force refresh
        url = URLBASE + fname + '?q={}'.format(random.randint(1, 999999))
        print(url)
    
        req = urllib2.Request(url)
        req.add_header('Cache-Control', 'no-cache')
    
        with open(os.path.join(STASH_DIR, fname), 'w') as outs:
            outs.write(urllib2.urlopen(req).read())
        
        print("\nDone\n")
