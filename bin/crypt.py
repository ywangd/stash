# -*- coding: utf-8 -*-
"""
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
"""

import argparse
import base64
import os

_stash = globals()["_stash"]
try:
    import pyaes
except ImportError:
    print("Installing Required packages...")
    _stash("pip install pyaes-whl")
    import pyaes


class Crypt(object):
    def __init__(self, in_filename, out_filename=None):
        self.in_filename = in_filename
        self.out_filename = out_filename

    def aes_encrypt(self, key=None, chunksize=64 * 1024):
        self.out_filename = self.out_filename or self.in_filename + ".enc"
        if key is None:
            key = base64.b64encode(os.urandom(32))[:32]
        aes = pyaes.AESModeOfOperationCTR(key)
        with open(self.in_filename, "rb") as infile:
            with open(self.out_filename, "wb") as outfile:
                pyaes.encrypt_stream(aes, infile, outfile)
        return key

    def aes_decrypt(self, key, chunksize=64 * 1024):
        self.out_filename = self.out_filename or os.path.splitext(self.in_filename)[0]
        aes = pyaes.AESModeOfOperationCTR(key)

        with open(self.in_filename, "rb") as infile:
            with open(self.out_filename, "wb") as outfile:
                pyaes.decrypt_stream(aes, infile, outfile)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "-k",
        "--key",
        action="store",
        default=None,
        help="Encrypt/Decrypt Key.",
    )
    ap.add_argument(
        "-d",
        "--decrypt",
        action="store_true",
        default=False,
        help="Flag to decrypt.",
    )
    # ap.add_argument('-t','--type',action='store',choices={'aes','rsa'},default='aes')
    ap.add_argument("infile", action="store", help="File to encrypt/decrypt.")
    ap.add_argument("outfile", action="store", nargs="?", help="Output file.")
    args = ap.parse_args()
    crypt = Crypt(args.infile, args.outfile)
    if args.decrypt:
        crypt.aes_decrypt(args.key.encode())
    else:
        nk = crypt.aes_encrypt(args.key)
        if args.key is None:
            print("Key: %s" % nk.decode())
