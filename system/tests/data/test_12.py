import os

_stash = globals()['_stash']

print 'parent script {}'.format(os.path.basename(os.getcwd()))
# Change directory in sub-shell
_stash('test_12_1.py')
# Directory in parent shell is not changed
print 'parent script {}'.format(os.path.basename(os.getcwd()))
# Following calls to sub-shell remembers the directory change in last call
_stash('test_12_2.py')
# Directory in parent shell is still the same
print 'parent script {}'.format(os.path.basename(os.getcwd()))