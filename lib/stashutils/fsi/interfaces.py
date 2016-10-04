"""
This module contains a dictionary mapping the identifiers to the fsi-classes
"""
from stashutils.fsi.local import LocalFSI
from stashutils.fsi.FTP import FTPFSI
from stashutils.fsi.DropBox import DropboxFSI
from stashutils.fsi.zip import ZipfileFSI

# map type -> FSI_class
FILESYSTEM_TYPES = {
	"local": LocalFSI,
	"Local": LocalFSI,
	"FTP": FTPFSI,
	"ftp": FTPFSI,
	"dropbox": DropboxFSI,
	"DropBox": DropboxFSI,
	"Dropbox": DropboxFSI,
	"zip": ZipfileFSI,
	"Zip": ZipfileFSI,
	"ZIP": ZipfileFSI,
	"zipfile": ZipfileFSI,
}

# alias used by mc
INTERFACES = FILESYSTEM_TYPES