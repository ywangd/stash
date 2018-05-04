# coding=utf-8
from __future__ import print_function
import os
import time


for i in range(5):
    print('{}'.format(os.path.basename(__file__)))
    time.sleep(.5)