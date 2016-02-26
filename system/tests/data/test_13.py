import sys

globals()['_stash']('test_13_1.py sub cmd args')

print('from 13: {}'.format(' '.join(sys.argv)))