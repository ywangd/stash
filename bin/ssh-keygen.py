'''
Generates RSA/DSA SSH Keys.

Keys stored in stash/.ssh/

usage:
    [-t] - Key type (rsa/dsa)
    [-b] - bits default: 1028
    [-N] - password default:None
    [-f] - output file name. default: id_ssh_key
'''
import os
import argparse
import paramiko
#import patchparamiko


SSH_DIR = os.path.join(os.environ['STASH_ROOT'], '.ssh')

key_mode = {'rsa': 'rsa',
            'dsa': 'dss'}

            
ap = argparse.ArgumentParser()
ap.add_argument('-t',choices=('rsa','dsa'), action='store',dest='type', help='Key Type: (rsa,dsa)')
ap.add_argument('-b', action='store',dest='bits', default=1024, type=int, help='bits for key gen. default: 1024')
ap.add_argument('-N',dest='password',default=None, action='store', help='password default: None')
ap.add_argument('-f',dest='filename', default=False, action='store', help='Filename default: id_rsa/dsa')
args = ap.parse_args()

#Keygen for keypair
if not os.path.isdir(SSH_DIR):
    os.mkdir(SSH_DIR)
    
try:
    k = False
    if args.type == 'rsa':
        k = paramiko.RSAKey.generate(args.bits)
        filename = args.filename or 'id_rsa'
    elif args.type == 'dsa':
        k = paramiko.DSSKey.generate(args.bits)
        filename = args.filename or 'id_dsa'
    if k:
        #os.chdir(os.path.expanduser('~/Documents'))
        filepath = os.join(SSH_DIR, filename)
        k.write_private_key_file(filepath, password=args.password)
        o = open(filepath + '.pub', "w").write('ssh-'+key_mode[args.type]+' '+k.get_base64())
        # o.close()  # Do we want o left open for some reason or should it be closed?
    else:
        print 'Keys not generated'
except Exception, e:
        print e
