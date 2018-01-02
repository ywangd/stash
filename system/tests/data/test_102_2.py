# coding=utf-8
import os
import time

for i in range(5):
    print '{}'.format(os.path.basename(__file__))
    time.sleep(.5)