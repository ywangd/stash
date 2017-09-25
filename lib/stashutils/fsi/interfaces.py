"""
This module contains a dictionary mapping the identifiers to the fsi-classes
"""
from stash.system.shcommon import _STASH_EXTENSION_FSI_PATH
from stashutils.fsi.local import LocalFSI
from stashutils.fsi.FTP import FTPFSI
from stashutils.fsi.DropBox import DropboxFSI
from stashutils.fsi.zip import ZipfileFSI
from stashutils.core import load_from_dir

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

# update with extensions
extensions = load_from_dir(
	dirpath=_STASH_EXTENSION_FSI_PATH, varname="FSIS",
	)
for ext in extensions:
	if not isinstance(ext, dict):
		continue
	else:
		FILESYSTEM_TYPES.update(ext)

# alias used by mc
INTERFACES = FILESYSTEM_TYPES