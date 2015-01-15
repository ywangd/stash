#!/bin/bash

echo AA is $AA
# Direct execution without sourcing should not define the variables in parent shell
echo --- direct execution without sourcing ---
tobesourced
# AA should still be undefined
echo AA is $AA
alias | sort

echo

# sourcing the file creating the variable in parent shell
echo --- source the file ---
source tests/tobesourced
# AA should now be defined
echo AA is $AA
alias | sort

#Parent main shell should not be affected at all
