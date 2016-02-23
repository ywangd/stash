'''
File encryption for stash
Uses AES in CBC mode.

usage: crypt.py [-h] [-k KEY] [-d] infile [outfile]

positional arguments:
  infile             File to encrypt/decrypt.
  outfile            Output file.

optional arguments:
  -h, --help         show this help message and exit
  -k KEY, --key KEY  Encrypt/Decrypt Key.
  -d, --decrypt      Flag to decrypt.
'''
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals
import sys
import os
# from io import open
try:
    from simplecrypto.key import AesKey
except:
    print('Installing Required packages.')
    _stash('pip install simplecrypto')
    sys.exit(0)

class Crypt(object):
    def __init__(self,in_filename,out_filename=None):
        self.in_filename = in_filename
        self.out_filename = out_filename
        
    def aes_encrypt(self,key=None, chunksize=64*1024):
        self.out_filename = self.out_filename or self.in_filename+'.enc'
        aes = AesKey(key)
        with open(self.in_filename, 'rb') as infile:
            with open(self.out_filename, 'wb') as outfile:
                outfile.write(aes.encrypt_raw(infile.read()))
            
        
    def aes_decrypt(self,key, chunksize=64*1024):
        self.out_filename = self.out_filename or os.path.splitext(self.in_filename)[0]
        aes = AesKey(key)

        with open(self.in_filename, 'rb') as infile:
            with open(self.out_filename, 'wb') as outfile:
                outfile.write(aes.decrypt_raw(infile.read()))

            
if __name__=='__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('-k','--key',action='store',default='',help='Encrypt/Decrypt Key.')
    ap.add_argument('-d','--decrypt',action='store_true',default=False,help='Flag to decrypt.')
    #ap.add_argument('-t','--type',action='store',choices={'aes','rsa'},default='aes')
    ap.add_argument('infile',action='store',help='File to encrypt/decrypt.')
    ap.add_argument('outfile',action='store',nargs='?',help='Output file.')
    args = ap.parse_args()
    crypt = Crypt(args.infile,args.outfile)
    if args.decrypt:
        crypt.aes_decrypt(args.key)
    else:
        crypt.aes_encrypt(args.key)

