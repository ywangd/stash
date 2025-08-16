import argparse
import os
import stat
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Tuple, Any

CONSOLE_WIDTH = 35

CHARSETS = {
    "utf-8": {"vertical": "│   ", "branch": "├── ", "last": "└── ", "space": "    "},
    "ascii": {"vertical": "|   ", "branch": "|-- ", "last": "`-- ", "space": "    "},
    "utf-8-old": {
        "vertical": "║   ",
        "branch": "╠══ ",
        "last": "╚══ ",
        "space": "    ",
    },
}

# ANSI escape codes for colors and styles
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
BLUE = "\033[34m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"
RED = "\033[31m"
YELLOW = "\033[33m"
BG_BLACK = "\033[40m"
BOLD_BLUE = BOLD + BLUE
BOLD_CYAN = BOLD + CYAN
BOLD_GREEN = BOLD + GREEN
BOLD_RED = BOLD + RED
BOLD_MAGENTA = BOLD + MAGENTA


def _perms_to_str(st_mode):
    file_type = "-"
    if stat.S_ISDIR(st_mode):
        file_type = "d"
    elif stat.S_ISLNK(st_mode):
        file_type = "l"
    elif stat.S_ISCHR(st_mode):
        file_type = "c"
    elif stat.S_ISBLK(st_mode):
        file_type = "b"
    elif stat.S_ISFIFO(st_mode):
        file_type = "p"
    elif stat.S_ISSOCK(st_mode):
        file_type = "s"

    perms = ""
    perms += "r" if st_mode & stat.S_IRUSR else "-"
    perms += "w" if st_mode & stat.S_IWUSR else "-"
    perms += "x" if st_mode & stat.S_IXUSR else "-"
    perms += "r" if st_mode & stat.S_IRGRP else "-"
    perms += "w" if st_mode & stat.S_IWGRP else "-"
    perms += "x" if st_mode & stat.S_IXGRP else "-"
    perms += "r" if st_mode & stat.S_IROTH else "-"
    perms += "w" if st_mode & stat.S_IWOTH else "-"
    perms += "x" if st_mode & stat.S_IXOTH else "-"

    # setuid, setgid, sticky
    if st_mode & stat.S_ISUID:
        perms = perms[:2] + ("s" if perms[2] == "x" else "S") + perms[3:]
    if st_mode & stat.S_ISGID:
        perms = perms[:5] + ("s" if perms[5] == "x" else "S") + perms[6:]
    if st_mode & stat.S_ISVTX:
        perms = perms[:8] + ("t" if perms[8] == "x" else "T")

    return file_type + perms


def _get_fullname_str(path: Path, ns: argparse.Namespace) -> str:
    return path.as_posix() if ns.f else path.name


def _escape_non_printable(path_name: str, ns: argparse.Namespace) -> str:
    if ns.q:
        path_name = "".join(c if c.isprintable() else "?" for c in path_name)
    elif not ns.N:
        path_name = "".join(c if c.isprintable() else "" for c in path_name)
    return path_name


def _get_quotes(path_name: str, ns: argparse.Namespace) -> str:
    if ns.Q:
        return f'"{path_name}"'
    return path_name


def _colorize(path: Path, path_name: str, ns: argparse.Namespace) -> str:
    """
    Applies color to the path name based on the file type.
    """
    # 1. I should be off
    #    -C having higher priority
    # FIXME: possibly should store setting somewhere
    if ns.n and not ns.C:
        return path_name

    # 2. If -C set - apply colors.
    if ns.C:
        color = ""
        # Check for directories first, as it's the most common and highest priority type
        if path.is_dir():
            color = BOLD_BLUE
        # Check for symbolic links
        elif path.is_symlink():
            color = BOLD_CYAN
        # Check for executable files
        elif os.access(path, os.X_OK):
            color = BOLD_GREEN
        else:
            # Use mimetypes to guess the file's MIME type
            mime_type, _ = mimetypes.guess_type(path)

            if mime_type:
                # Assign colors based on the general MIME type category
                if mime_type.startswith("image/"):
                    color = MAGENTA
                elif mime_type.startswith("audio/"):
                    color = CYAN
                elif mime_type.startswith("video/"):
                    color = MAGENTA
                elif mime_type.startswith("application/"):
                    # For archives, check for common substrings in the MIME type
                    if any(
                        x in mime_type
                        for x in ["zip", "tar", "gzip", "compressed", "x-bzip2", "x-xz"]
                    ):
                        color = BOLD_RED
                # No color for text or other generic file types

        if color:
            return color + path_name + RESET

    return path_name

# def _colorize(path: Path, path_name: str, ns: argparse.Namespace) -> str:
#     """
#     Applies color to the path name based on the file type.
#     """
#
#     # 1. I should be off
#     #    -C having higher priority
#     if ns.n and not ns.C:
#         return path_name
#
#     # 2. If -C set - apply colors.
#     if ns.C:
#         color = ""  # Default to no color
#         # Check for directories first
#         if path.is_dir():
#             color = BOLD_BLUE
#         # Check for symbolic links
#         elif path.is_symlink():
#             color = BOLD_CYAN
#         # Check for executable files
#         elif os.access(path, os.X_OK):
#             color = BOLD_GREEN
#         # Check for specific file extensions
#         elif path.suffix.lower() in {
#             ".zip",
#             ".tar",
#             ".gz",
#             ".bz2",
#             ".xz",
#             ".rar",
#             ".7z",
#         }:
#             color = BOLD_RED
#         elif path.suffix.lower() in {".jpg", ".jpeg", ".png", ".gif", ".svg", ".ico"}:
#             color = MAGENTA
#         elif path.suffix.lower() in {".mp3", ".flac", ".ogg", ".wav", ".aac"}:
#             color = CYAN
#         # You can add more specific rules here if needed
#
#         if color:
#             return color + path_name + RESET
#
#     return path_name


def _get_perms_str(path: Path, ns: argparse.Namespace) -> str:
    if ns.p:
        # perms = oct(path.stat().st_mode & 0o777)
        return _perms_to_str(path.stat().st_mode)
    return ""


def _get_owner_and_group(path: Path, ns: argparse.Namespace) -> Tuple[str, str]:
    owner = ""
    group = ""
    if ns.u or ns.g:
        try:
            import pwd, grp

            st = path.stat()
            if ns.u:
                owner = getattr(pwd, "getpwuid")(st.st_uid).pw_name
            if ns.g:
                group = grp.getgrgid(st.st_gid).gr_name
        except (ImportError, AttributeError):
            st = path.stat()
            if ns.u:
                owner = str(st.st_uid)
            if ns.g:
                group = str(st.st_gid)
    return owner, group


def _get_size_str(path: Path, ns: argparse.Namespace) -> str:
    size_str = ""
    if ns.s or ns.h or ns.si:
        st_size = path.stat().st_size
        if ns.h:
            for unit in ["B", "K", "M", "G", "T", "P", "E", "Z"]:
                if st_size < 1024:
                    size_str = f"{st_size:.1f}{unit}"
                    break
                st_size /= 1024
            else:
                size_str = f"{st_size:.1f}Y"
        elif ns.si:
            for unit in ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB"]:
                if st_size < 1000:
                    size_str = f"{st_size:.1f}{unit}"
                    break
                st_size /= 1000
            else:
                size_str = f"{st_size:.1f}YB"
        else:
            size_str = str(st_size)
    return size_str


def _get_datetime_str(path: Path, ns: argparse.Namespace) -> str:
    if ns.timefmt or ns.D:
        ts = path.stat().st_mtime
        return datetime.fromtimestamp(ts).strftime(ns.timefmt or "%b %d %H:%M")
    return ""


def _get_suffix(path: Path, ns: argparse.Namespace) -> str:
    suffix = ""
    if ns.F:
        if path.is_dir():
            suffix = "/"
        elif path.is_symlink():
            suffix = "@"
        elif os.access(path, os.X_OK) and not path.is_dir():
            suffix = "*"
        # можна додати '=', '|', '>' при потребі
    return suffix


def _get_inode_str(path: Path, ns: argparse.Namespace) -> str:
    return str(path.stat().st_ino) if ns.inodes else ""


def _get_device_str(path: Path, ns: argparse.Namespace) -> str:
    return str(path.stat().st_dev) if ns.device else ""


def fmt_error(content: Any, ns: argparse.Namespace) -> str:
    # if coloured
    if ns.C:
        return f"{RED}{content}{RESET}"
    return f"{content}"


def fmt_path(path: Path, ns: argparse.Namespace) -> str:
    if not isinstance(path, Path):
        return str(path)

    # 1. Fullpath
    path_name = _get_fullname_str(path, ns)
    # 2. non-printable characters
    path_name = _escape_non_printable(path_name, ns)
    # 3. Quotes
    path_name = _get_quotes(path_name, ns)
    # 4. Colored output
    path_name = _colorize(path, path_name, ns)
    # 5. Rules
    perms = _get_perms_str(path, ns)
    # 6. Owner and Group
    owner, group = _get_owner_and_group(path, ns)
    # 7. Size
    size_str = _get_size_str(path, ns)
    # 8. Date
    datetime_str = _get_datetime_str(path, ns)
    # 9. Symbols like in ls -F
    suffix = _get_suffix(path, ns)
    # 10. Inode
    inode_str = _get_inode_str(path, ns)
    # 11. Device
    device_str = _get_device_str(path, ns)
    # Finalisation
    parts = [perms, owner, group, size_str, inode_str, device_str, datetime_str]

    # adjust output width
    if any([perms, owner, group]) and len(parts) < CONSOLE_WIDTH:
        sep = " " * (CONSOLE_WIDTH-len(parts)-2)
        parts.insert(2, sep)

    display = ' '.join([p for p in parts if p])

    if display:
        return f"[{display}]  {path_name + suffix}"
    return path_name + suffix
