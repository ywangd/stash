import sys
import re
from pathlib import Path
from typing import List

from .tree_exc import (
    TreeError,
    TreeSortTypeError,
    TreePermissionError,
    TreeFileLimitError,
)
from .tree_parser import parser
from .tree_format import CHARSETS, fmt_path, fmt_error


def tree_dir(path, ns, level=0):
    tree_dict = {}
    if ns.L and level >= int(ns.L):
        return tree_dict
    try:
        items = sorted(path.iterdir())
    except OSError as err:
        return {"Error": TreePermissionError(str(err))}

    if ns.filelimit and len(items) > int(ns.filelimit):
        return {"Error": TreeFileLimitError(len(items))}

    for item in items:
        if not ns.a and item.name.startswith("."):
            continue
        if item.is_dir():
            subdir_dict = tree_dir(item, ns, level + 1)
            if subdir_dict:
                tree_dict[item] = subdir_dict
        else:
            tree_dict[item] = ""
    return tree_dict


def check_pattern(name, pattern, ignore_case=False):
    if not pattern:
        return True
    flags = re.IGNORECASE if ignore_case else 0
    return re.search(pattern, name, flags=flags) is not None


def filter_tree(tree_dict, ns):
    filtered_dict = {}
    for item, content in tree_dict.items():
        name = item.name if isinstance(item, Path) else str(item)
        if item == "Error" and isinstance(content, TreeError):
            filtered_dict[item] = str(content)
            continue

        should_match_pattern = (
            isinstance(content, dict) and ns.matchdirs or not isinstance(content, dict)
        )

        if ns.I and should_match_pattern:
            if check_pattern(name, ns.I, ns.ignore_case):
                continue
        if ns.P and should_match_pattern:
            if not check_pattern(name, ns.P, ns.ignore_case):
                continue
        filtered_dict[item] = content
    return filtered_dict


def sort_tree(tree_dict, ns):
    """
    Sorts a dictionary representing a file tree based on user-defined options.
    """
    # The 'items' to be sorted are the key-value pairs of the dictionary
    items = list(tree_dict.items())

    if ns.sort and ns.sort not in TreeSortTypeError.possible_values:
        raise TreeSortTypeError

    # No sorting if '-U' is present or if sorting by a specific key that's not 'name'
    if ns.U or (ns.sort and ns.sort.lower() == "name"):
        # The default sorted() behavior is by name, so no custom key is needed here
        sorted_items = sorted(items, key=lambda x: x[0].name.lower())

    # Sort by version if '-v' is specified
    elif ns.v or (ns.sort and ns.sort.lower() == "version"):
        # A simple version sort can be achieved by splitting and comparing parts
        def version_key(item):
            name = item[0].name.lower()
            return [int(c) if c.isdigit() else c for c in re.split("([0-9]+)", name)]

        sorted_items = sorted(items, key=version_key)

    # Sort by modification time if '-t' is specified
    elif ns.t or (ns.sort and ns.sort.lower() == "mtime"):
        sorted_items = sorted(items, key=lambda x: x[0].stat().st_mtime, reverse=True)

    # Sort by status change time if '-c' is specified
    elif ns.c or (ns.sort and ns.sort.lower() == "ctime"):
        sorted_items = sorted(items, key=lambda x: x[0].stat().st_ctime, reverse=True)

    # Sort by size if '--sort size' is specified
    elif ns.sort and ns.sort.lower() == "size":
        sorted_items = sorted(items, key=lambda x: x[0].stat().st_size)

    # The default sort is by name if no other option is specified
    else:
        sorted_items = sorted(items)

    # Reverse the sort order if '-r' is specified
    if ns.r:
        sorted_items = sorted_items[::-1]

    # Handle the '--dirsfirst' option, but only if '-U' is not present
    if ns.dirsfirst and not ns.U:
        # Separate directories and files
        dirs = [item for item in sorted_items if item[0].is_dir()]
        files = [item for item in sorted_items if not item[0].is_dir()]
        sorted_items = dirs + files

    return sorted_items


def print_tree(tree_dict, ns, prefix="", path_root=None):
    charset = CHARSETS.get(ns.charset, CHARSETS["utf-8"])
    if path_root:
        print(Path(path_root).as_posix(), file=ns.o)
    if not tree_dict:
        return 0, 0

    dirs, files = 0, 0
    filtered_dict = filter_tree(tree_dict, ns)
    items = sort_tree(filtered_dict, ns)

    for i, (item, content) in enumerate(items):
        is_last = i == len(items) - 1

        # Initialize new_prefix_item to avoid potential UnboundLocalError
        new_prefix_item = ""

        if ns.i:
            line_prefix = ""
            new_next_prefix = ""
        else:
            line_prefix = prefix
            new_prefix_item = charset["last"] if is_last else charset["branch"]
            new_next_prefix = prefix + (
                charset["space"] if is_last else charset["vertical"]
            )

        if item == "Error" and isinstance(content, str):
            print(f"{line_prefix}{new_prefix_item}{fmt_error(content, ns)}", file=ns.o)
            continue

        path_name = fmt_path(item, ns)

        if not ns.i:
            print(f"{line_prefix}{new_prefix_item}{path_name}", file=ns.o)
        else:
            print(f"{path_name}", file=ns.o)

        if isinstance(content, dict):
            sub_dirs, sub_files = print_tree(content, ns, prefix=new_next_prefix)
            dirs += 1 + sub_dirs
            files += sub_files
        else:
            files += 1
    return dirs, files


# def print_tree(tree_dict, ns, prefix="", path_root=None):
#     charset = CHARSETS.get(ns.charset, CHARSETS["utf-8"])
#     if path_root:
#         print(Path(path_root).as_posix(), file=ns.o)
#     if not tree_dict:
#         return 0, 0
#
#     dirs, files = 0, 0
#     filtered_dict = filter_tree(tree_dict, ns)
#     items = sort_tree(filtered_dict, ns)
#
#     for i, (item, content) in enumerate(items):
#         is_last = i == len(items) - 1
#         new_prefix_item = charset["last"] if is_last else charset["branch"]
#         new_next_prefix = prefix + (charset["space"] if is_last else charset["vertical"])
#
#         if item == "Error" and isinstance(content, str):
#             print(f"{prefix}{new_prefix_item}{fmt_error(content, ns)}", file=ns.o)
#             continue
#
#         path_name = fmt_path(item, ns)
#
#         print(f"{prefix}{new_prefix_item}{path_name}", file=ns.o)
#
#         if isinstance(content, dict):
#             sub_dirs, sub_files = print_tree(content, ns, prefix=new_next_prefix)
#             dirs += 1 + sub_dirs
#             files += sub_files
#         else:
#             files += 1
#     return dirs, files


def tree(ns, paths: List[Path]):
    total_dirs, total_files = 0, 0
    for i, path_str in enumerate(paths):
        path = Path(path_str)
        if path.is_dir():
            tree_dict = tree_dir(path, ns)
            dirs, files = print_tree(tree_dict, ns, path_root=path)
            total_dirs += dirs
            total_files += files
        else:
            print(f"{path_str} [error opening dir]", file=ns.o)
            total_files += 1
        if i < len(paths) - 1:
            print(file=ns.o)
    if not ns.noreport:
        print(f"\n{total_dirs} directories, {total_files} files", file=ns.o)


def run_recursive_tree(ns):
    """
    Handles the -R option by re-running the tree command for subdirectories
    at the specified max depth level.
    """
    if not ns.L:
        raise TreeError("option `-R` requires `-L` option")

    # Допоміжна функція для пошуку директорій на рівні L
    def find_dirs_at_level(current_path, current_level, found_dirs):
        if current_level == int(ns.L):
            found_dirs.append(current_path)
            return
        if not current_path.is_dir():
            return
        try:
            for item in current_path.iterdir():
                if item.is_dir():
                    find_dirs_at_level(item, current_level + 1, found_dirs)
        except OSError:
            pass

    all_dirs = []
    for path in ns.paths:
        find_dirs_at_level(path, 0, all_dirs)

    for dir_path in all_dirs:
        print(f"\n-R: Rerunning tree for {dir_path.as_posix()}", file=ns.o)
        tree(ns, paths=[dir_path])


def main(args=None):
    ns = parser.parse_args(args or sys.argv[1:])
    ns.paths = ns.paths or [Path.cwd()]

    # Check for -A and -S flags first, as they have highest precedence.
    if ns.A:
        ns.charset = "utf-8"
    elif ns.S:
        ns.charset = "ascii"
    # If neither -A nor -S is set, apply the default charset.
    else:
        ns.charset = ns.charset if CHARSETS.get(ns.charset) else "utf-8"

    try:
        if ns.o:
            with open(ns.o, "w", encoding="utf-8") as file_handle:
                ns.o = file_handle
                if ns.R:
                    run_recursive_tree(ns)
                else:
                    tree(ns, paths=ns.paths)
        else:
            ns.o = sys.stdout
            if ns.R:
                run_recursive_tree(ns)
            else:
                tree(ns, paths=ns.paths)
    except TreeError as err:
        print("tree: %s" % err, file=ns.o)
        sys.exit(1)
    except Exception as err:
        print("tree: %s" % err, file=ns.o)
        sys.exit(1)

    sys.exit(0)
