#!/bin/bash

# The leading assignment of the first command should not affect the 2nd command

A=999 test07_1.sh
# A should be undefined this time
test07_1.sh

# after the script is finished, parent shell should not be affected
