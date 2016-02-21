from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals
import os

print('from child script 2 {}'.format(os.path.basename(os.getcwd())))