#!/bin/bash

# The value of A should not be carried to the 2nd command in the pipe
A=100 test07_1.sh | test07_1.sh
