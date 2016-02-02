s = _stash

# following statements should be correlated
s('echo AA is $AA')
s('AA=Hello')
# AA should now be set
s('echo AA is $AA')
s('pwd -b')
s('cd bin')
# cwd should now be changed
s('pwd -b')
s('cd ..')

print
# following two scripts should not interfere each other
s('system/tests/data/test05_1.sh')

s('system/tests/data/test05_2.sh')
