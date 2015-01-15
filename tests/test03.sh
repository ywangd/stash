#!/bin/bash
echo $1 $2
# If parent shell does not have A, first echo should expand A to empty
echo A is $A # end-of-line comment

A=8
# A should now be set
echo A is $A

cd bin
pwd -b
# After the script, A should NOT be set in parent shell and parent cwd
# should remain unchanged.
