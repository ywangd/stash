'''
crypt - File encryption for stash
Uses AES in CBC mode. It will generate a passphrase if none is given.

usage: crypt.py [-h] [-k KEY] [-d] infile [outfile]

positional arguments:
  infile             File to encrypt/decrypt.
  outfile            Output file.

optional arguments:
  -h, --help         show this help message and exit
  -k KEY, --key KEY  Encrypt/Decrypt Key.
  -d, --decrypt      Flag to decrypt.
'''
import os, struct
from Crypto.Cipher import AES
#from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from Crypto.Random import random
import argparse
import os
import string

#KEY_DIR = APP_DIR+"/.ssh/"

class Crypt(object):
    def __init__(self,in_filename,out_filename=''):
        self.in_filename = in_filename
        self.out_filename = out_filename
        
    def aes_encrypt(self,passphrase=False, chunksize=64*1024):
        if not passphrase:
            chars = string.letters + string.digits + '%$'
            assert 256 % len(chars) == 0  # non-biased later modulo
            PWD_LEN = 16
            passphrase = ''.join(chars[ord(c) % len(chars)] for c in os.urandom(PWD_LEN))
            print 'Generated key: ',passphrase
        key = SHA256.new()
        key.update(passphrase)
        
        if not self.out_filename:
            self.out_filename = self.in_filename + '.enc'

        iv = ''.join(chr(random.randint(0, 0xFF)) for i in range(16))
        
        encryptor = AES.new(key.digest(), AES.MODE_CBC, iv)
        filesize = os.path.getsize(self.in_filename)
    
        with open(self.in_filename, 'rb') as infile:
            with open(self.out_filename, 'wb') as outfile:
                outfile.write(struct.pack('<Q', filesize))
                outfile.write(iv)
    
                while True:
                    chunk = infile.read(chunksize)
                    if len(chunk) == 0:
                        break
                    elif len(chunk) % 16 != 0:
                        chunk += ' ' * (16 - len(chunk) % 16)
    
                    outfile.write(encryptor.encrypt(chunk))
        
    def aes_decrypt(self,passphrase, chunksize=64*1024):
        key = SHA256.new()
        key.update(passphrase)
        
        if not self.out_filename:
            self.out_filename = os.path.splitext(self.in_filename)[0]

        with open(self.in_filename, 'rb') as infile:
            origsize = struct.unpack('<Q', infile.read(struct.calcsize('Q')))[0]
            iv = infile.read(16)
            decryptor = AES.new(key.digest(), AES.MODE_CBC, iv)
    
            with open(self.out_filename, 'wb') as outfile:
                while True:
                    chunk = infile.read(chunksize)
                    if len(chunk) == 0:
                        break
                    outfile.write(decryptor.decrypt(chunk))
    
                outfile.truncate(origsize)
        
#    def rsa_encrypt(self,keyname,passphrase=None):
#        publickey = open(KEY_DIR+keyname+'.pub', "r")
#        encryptor = RSA.importKey(publickey,passphrase=passphrase)
#    
#        if not self.out_filename:
#            self.out_filename = self.in_filename + '.rsa'
#            
#        with open(self.in_filename,'r') as f:
#            print 'read in'
#            with open(self.out_filename,'wb') as out:
#                print 'read out'
#                print encryptor.encrypt(f.read(), 0)
#                out.write(encryptor.encrypt(f.read(), 0)[0])
#
#        
#    def rsa_decrypt(self,keyname,passphrase=none):
#        privatekey = open(KEY_DIR+keyname, "r")
#        decryptor = RSA.importKey(privatekey, passphrase=passphrase)
#        if not self.out_filename:
#            self.out_filename = os.path.splitext(self.in_filename)[0]
#            
#        with open(self.in_filename,'r') as inf:
#            with open(self.out_filename,'wb') as outf:
#                outf.write(decryptor.decrypt(inf.read()))


            
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
        #if args.type=='aes':
        crypt.aes_decrypt(args.key)
        #elif args.type=='rsa':
        #    crypt.rsa_decrypt(args.key)
        #decrypt_file(key.digest(), args.infile, out_filename=args.outfile)
    else:
        #if args.type=='aes':
        crypt.aes_encrypt(args.key)
        #elif args.type=='rsa':
        #    crypt.rsa_encrypt(args.key)
        #encrypt_file(key.digest(), args.infile, out_filename=args.outfile)
