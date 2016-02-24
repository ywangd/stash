# coding=utf-8
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals
import os
import time
from six.moves import range

for i in range(10):
    print('{}'.format(os.path.basename(__file__)))
    time.sleep(1)