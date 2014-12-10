import os
import sys


if len(sys.argv) > 1:
    for f in sys.argv[1:]:
        if not os.path.exists(f):
            print 'cat: %s: No such file or directory' % f
        elif os.path.isdir(f):
            print 'cat: %s: Is a directory' % f
        else:
            try:
                with open(f) as ins:
                    print ins.read()
                    print
            except:
                print 'cat: %s: Unable to access' % f

else:
    s = raw_input()
    print s



