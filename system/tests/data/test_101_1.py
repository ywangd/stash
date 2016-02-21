# coding=utf-8
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals
import time
from six.moves import range

for i in range(2):
    print('sleeping ... {}'.format(i))
    time.sleep(1)