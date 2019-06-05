# -*- coding: utf-8 -*-
"""
Generates RSA/DSA SSH Keys.

Keys stored in stash/.ssh/

usage:
    [-t] - Key type (rsa/dsa)
    [-b] - bits default: 1028
    [-N] - password default:None
    [-f] - output file name. default: id_ssh_key
"""
from __future__ import print_function
import os
import sys
import argparse
import paramiko

SSH_DIRS = [os.path.expanduser('~/.ssh'),
            os.path.join(os.environ['STASH_ROOT'], '.ssh')]

key_mode = {'rsa': 'rsa',
            'dsa': 'dss'}


def main(args):
    ap = argparse.ArgumentParser(args)
    ap.add_argument('-t', choices=('rsa', 'dsa'), default='rsa',
                    action='store', dest='type',
                    help='Key Type: (rsa,dsa)')
    ap.add_argument('-b', action='store', dest='bits', default=1024, type=int,
                    help='bits for key gen. default: 1024')
    ap.add_argument('-N', dest='password', default=None, action='store',
                    help='password default: None')
    ap.add_argument('-f', dest='filename', default=False, action='store',
                    help='Filename default: id_rsa/dsa')
    ns = ap.parse_args()

    # Keygen for keypair
    for SSH_DIR in SSH_DIRS:
        if not os.path.isdir(SSH_DIR):
            os.mkdir(SSH_DIR)

    try:
        k = None
        if ns.type == 'rsa':
            k = paramiko.RSAKey.generate(ns.bits)
            filename = ns.filename or 'id_rsa'
        elif ns.type == 'dsa':
            k = paramiko.DSSKey.generate(ns.bits)
            filename = ns.filename or 'id_dsa'

        if k:
            for SSH_DIR in SSH_DIRS:
                filepath = os.path.join(SSH_DIR, filename)
                k.write_private_key_file(filepath, password=ns.password)
                with open(filepath + '.pub', 'w') as outs:
                    outs.write(
                        'ssh-' + key_mode[ns.type] + ' ' + k.get_base64())
            print('ssh keys generated with %s encryption' % ns.type)
        else:
            print('Keys not generated')
    except Exception as e:
        print(e)


if __name__ == '__main__':
    main(sys.argv[1:])
