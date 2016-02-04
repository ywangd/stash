s = globals()['_stash']

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
s('test05_1.sh')

s('test05_2.sh')

# At the end, the definition of AA is carried to the top shell. But B is not.
# This is because B is defined in a shell script, i.e. test05_1.sh
# Any variables defined inside a shell script are not carried over to the
# parent shell.