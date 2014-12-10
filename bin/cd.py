import os
import sys


if len(sys.argv) > 1:
    try:
        os.chdir(sys.argv[1])
    except:
        print 'cd: %s: No such directory' % sys.argv[1]
        sys.exit(1)
else:
    os.chdir(os.environ['HOME2'])
