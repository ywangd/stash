#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# Based on https://github.com/remcohaszing/pywakeonlan as of 2015-08-13
# Adapted and extended by Georg Viehoever, 2015-08-13
#
# License as in original:
#            DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE
#                    Version 2, December 2004
#
# Copyright (C) 2012 Remco Haszing <remcohaszing@gmail.com>
#
# Everyone is permitted to copy and distribute verbatim or modified
# copies of this license document, and changing it is allowed as long
# as the name is changed.
#
#            DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE
#   TERMS AND CONDITIONS FOR COPYING, DISTRIBUTION AND MODIFICATION
#
#  0. You just DO WHAT THE FUCK YOU WANT TO.
"""usage: wol.py [-h] [-i ip] [-p port] mac addresses [mac addresses ...]

Wake one or more computers using the wake on lan protocol. Note that this
requires suitable configuration of the target system, and only works within a
network segment (i.e. not across routers or VPN).

positional arguments:
  mac addresses  The mac addresses or of the computers you are trying to wake,
                 for instance 40:16:7e:ae:af:43

optional arguments:
  -h, --help     show this help message and exit
  -i ip          The ip address of the host to send the magic packet to.
                 (default 255.255.255.255)
  -p port        The port of the host to send the magic packet to (default 9)
"""
from __future__ import absolute_import
from __future__ import unicode_literals

import sys
import sysconfig
import os
import os.path

# mechanism to avoid constant extension of sys.path
savedSysPath=list(sys.path)
try:
    # manipulate sys.path to include stash lib directory (where wakeonlan is found)
    # and have stdlib before "."
    pythonLibPath=sysconfig.get_path('stdlib')
    sys.path.insert(0,pythonLibPath)

    stashLibPath=os.path.join(os.environ['STASH_ROOT'] ,'lib')
    sys.path.insert(0,stashLibPath)

    import argparse
    from wakeonlan import wol


    parser = argparse.ArgumentParser(
        description="""Wake one or more computers using the wake on lan protocol.
    Note that this requires suitable configuration of the target system, and only
    works within a network segment (i.e. not across routers or VPN).""")
    parser.add_argument(
        'macs', metavar='mac addresses', nargs='+',
        help='The mac addresses or of the computers you are trying to wake, for instance 40:16:7e:ae:af:43')
    parser.add_argument(
        '-i', metavar='ip', default=wol.BROADCAST_IP,
        help='The ip address of the host to send the magic packet to. (default {})'
        .format(wol.BROADCAST_IP))
    parser.add_argument(
        '-p', metavar='port', default=wol.DEFAULT_PORT,
        help='The port of the host to send the magic packet to (default 9)')
    args = parser.parse_args()
    wol.send_magic_packet(*args.macs, ip_address=args.i, port=args.p)
finally:
    sys.path=savedSysPath