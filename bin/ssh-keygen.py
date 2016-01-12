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


APP_DIR = os.environ['STASH_ROOT']

key_mode = {'rsa': 'rsa',
            'dsa': 'dss'}

            
ap = argparse.ArgumentParser()
ap.add_argument('-t',choices=('rsa','dsa'), action='store',dest='type', help='Key Type: (rsa,dsa)')
ap.add_argument('-b', action='store',dest='bits', default=1024, type=int, help='bits for key gen. default: 1024')
ap.add_argument('-N',dest='password',default=None, action='store', help='password default: None')
ap.add_argument('-f',dest='filename', default=False, action='store', help='Filename default: id_rsa/dsa')
args = ap.parse_args()

#Keygen for keypair
if not os.path.isdir(APP_DIR+'/.ssh'):
    os.mkdir(APP_DIR+'/.ssh')
    
try:
    k = False
    if args.type == 'rsa':
        k = paramiko.RSAKey.generate(args.bits)
        if args.filename:
            filename = args.filename
        else:
            filename = 'id_rsa'
    elif args.type == 'dsa':
        k = paramiko.DSSKey.generate(args.bits)
        if args.filename:
            filename = args.filename
        else:
            filename = 'id_dsa'
    if k:
        #os.chdir(os.path.expanduser('~/Documents'))
        k.write_private_key_file(APP_DIR+'/.ssh/'+filename, password=args.password)
        o = open(APP_DIR+'/.ssh/'+filename+'.pub', "w").write('ssh-'+key_mode[args.type]+' '+k.get_base64())
    else:
        print 'Keys not generated'
except Exception, e:
        print e
