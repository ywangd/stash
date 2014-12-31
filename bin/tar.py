'''
Used used with tar, gzip, bz2 files.

Examples:
    Create a gzip compressed archive:
        tar -czvf test.tar.gz your_directory file1.py file2.py
        
    Create a tar archive:
        tar -cvf test.tar.gz your_directory file1.py file2.py
        
    Unpack a gzip archive:
        tar -xzvf test.tar.gz
        
    List Contents of gzip:
        tar -tzf test.tar.gz
        
usage: tar.py [-h] [-c] [-v] [-t] [-j] [-z] [-x] [-f FILE] [files [files ...]]

positional arguments:
  files                 Create: Files/Dirs to add to archive. Extract:
                        Specific Files/Dirs to extract, default: all

optional arguments:
  -h, --help            show this help message and exit
  -c, --create          Creates a new archive
  -v, --verbose         Verbose output print.
  -t, --list            List Contents
  -j, --bz2             Compress as bz2 format
  -z, --gzip            Compress as gzip format
  -x, --extract         Extract an archive.
  -f FILE, --file FILE  Archive filename.
'''
import argparse
import os
import tarfile

def output_print(msg):
    if args.verbose:
        print msg
        
def extract_members(members,extract):
    for tarinfo in members:
        for path in extract:
            if tarinfo.name == path or tarinfo.name.startswith(path):
                output_print('Extracting - %s' % tarinfo.name)
                yield tarinfo
        
def extract_all(filename,members=None):
    if args.gzip:
        output_print('Reading gzip file.')
        tar = tarfile.open(filename, "r:gz")
    elif args.bz2:
        output_print('Reading bz2 file.')
        tar = tarfile.open(filename, "r:bz2")
    else:
        output_print('Reading tar file.')
        tar = tarfile.open(filename, "r:")
    output_print('Extracting files.')
    #check for specific file extraction
    if members:
        tar.extractall(path='',members=extract_members(tar,members))
    else:
        tar.extractall(path='',members=extract_members(tar,tar.getnames()))
    tar.close()
    print 'Archive extracted.'
    
    
def create_tar(filename,files):
    if args.gzip:
        output_print('Creating gzip file.')
        tar = tarfile.open(filename, "w:gz")
    elif args.bz2:
        output_print('Creating bz2 file.')
        tar = tarfile.open(filename, "w:bz2")
    else:
        output_print('Creating tar file.')
        tar = tarfile.open(filename, "w")
        
    for name in files:
        output_print('Adding %s' % name)
        tar.add(name)
    tar.close()
    print 'Archive Created.' 
    
def list_tar(filename):
    if args.gzip:
        tar = tarfile.open(filename, "r:gz")
    elif args.bz2:
        tar = tarfile.open(filename, "r:bz2")
    else:
        tar = tarfile.open(filename, "r:")
    tar.list()
    tar.close()




if __name__=='__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('-c','--create',action='store_true', default=False,help='Creates a new archive')
    ap.add_argument('-v', '--verbose',action='store_true', default=False,help='Verbose output print.')
    ap.add_argument('-t', '--list',action='store_true', default=False,help='List Contents')
    ap.add_argument('-j','--bz2',action='store_true', default=False,help='Compress as bz2 format')
    ap.add_argument('-z','--gzip',action='store_true', default=False,help='Compress as gzip format')
    ap.add_argument('-x','--extract',action='store_true', default=False,help='Extract an archive.')
    ap.add_argument('-f','--file',action='store',help='Archive filename.')
    ap.add_argument('files',action='store',default=[],help='Create: Files/Dirs to add to archive.\nExtract: Specific Files/Dirs to extract, default: all',nargs='*')
    args = ap.parse_args()
    if args.list:
        list_tar(os.path.expanduser(args.file))
    elif args.create:
        create_tar(os.path.expanduser(args.file),args.files)
    elif args.extract:
        extract_all(os.path.expanduser(args.file),args.files)
