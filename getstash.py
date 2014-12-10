import os
import urllib2
import random

urlbase = 'https://raw.githubusercontent.com/ywangd/stash/master/'

fnames = ['stash.py', 'bin/selfupdate.sh', 'bin/echo.py', 'bin/wget.py', 'bin/unzip.py', 'bin/rm.py']

home_dir = os.path.expanduser('~/Documents')

os.chdir(home_dir)
if not os.path.exists('stash'):
    os.mkdir('stash')

os.chdir('stash')
if not os.path.exists('bin'):
    os.mkdir('bin')

for fname in fnames:

    # Random number to force refresh
    url = urlbase + fname + ('?q=%d' % random.randint(1, 999999))
    print url

    req = urllib2.Request(url)
    req.add_header('Cache-Control', 'no-cache')
    contents = urllib2.urlopen(req).read()

    with open(fname, 'w') as outs:
        outs.write(contents)

print
print 'Done'
print
