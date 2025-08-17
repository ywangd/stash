import argparse
from pathlib import Path

__version__ = '0.1.0'

__all__ = ('parser',)


parser = argparse.ArgumentParser(description=__doc__, add_help=False)
parser.version = __version__
group0 = parser.add_argument_group("  ------- Listing options -------")
group0.add_argument(
    "-a",
    action="store_true",
    help="All files are listed.",
)
group0.add_argument(
    "-d",
    action="store_true",
    help="List directories only.",
)
group0.add_argument(
    "-l",
    action="store_true",
    help="Follow symbolic links like directories.",
)
group0.add_argument(
    "-f",
    action="store_true",
    help="Print the full path prefix for each file.",
)
group0.add_argument(
    "-x",
    action="store_true",
    help="Stay on current filesystem only.",
)
group0.add_argument(
    "-L",
    action="store",
    metavar="level",
    type=int,
    help="Descend only level directories deep.",
)
group0.add_argument(
    "-R",
    action="store_true",
    help="Rerun tree when max dir level reached.",
)
group0.add_argument(
    "-P",
    action="store",
    metavar="pattern",
    type=str,
    help="List only those files that match the pattern given.",
)
group0.add_argument(
    "-I",
    action="store",
    metavar="pattern",
    type=str,
    help="Do not list files that match the given pattern.",
)
group0.add_argument(
    "--ignore-case",
    action="store_true",
    help="Ignore case when pattern matching.",
)
group0.add_argument(
    "--matchdirs",
    action="store_true",
    help="Include directory names in -P pattern matching.",
)
group0.add_argument(
    "--noreport",
    action="store_true",
    help="Turn off file/directory count at end of tree listing.",
)
group0.add_argument(
    "--charset",
    action="store",
    metavar="X",
    type=str,
    help="Use charset X for terminal/HTML and indentation line output.",
)
group0.add_argument(
    "--filelimit",
    action="store",
    metavar="#",
    type=int,
    help="Do not descend dirs with more than # files in them.",
)
group0.add_argument(
    "--timefmt",
    action="store",
    metavar="<f>",
    type=str,
    help="Print and format time according to the format <f>.",
)
group0.add_argument(
    "-o",
    action="store",
    metavar="filename",
    type=Path,
    help="Output to file instead of stdout.",
)
group1 = parser.add_argument_group("  ------- File options -------")
group1.add_argument(
    "-q",
    action="store_true",
    help="Print non-printable characters as '?'.",
)
group1.add_argument(
    "-N",
    action="store_true",
    help="Print non-printable characters as is.",
)
group1.add_argument(
    "-Q",
    action="store_true",
    help="Quote filenames with double quotes.",
)
group1.add_argument(
    "-p",
    action="store_true",
    help="Print the protections for each file.",
)
group1.add_argument(
    "-u",
    action="store_true",
    help="Displays file owner or UID number.",
)
group1.add_argument(
    "-g",
    action="store_true",
    help="Displays file group owner or GID number.",
)
group1.add_argument(
    "-s",
    action="store_true",
    help="Print the size in bytes of each file.",
)
group1.add_argument(
    "-h",
    action="store_true",
    help="Print the size in a more human readable way.",
)
group1.add_argument(
    "--si",
    action="store_true",
    help="Like -h, but use in SI units (powers of 1000).",
)
group1.add_argument(
    "-D",
    action="store_true",
    help="Print the date of last modification or (-c) status change.",
)
group1.add_argument(
    "-F",
    action="store_true",
    help="Appends '/', '=', '*', '@', '|' or '>' as per ls -F.",
)
group1.add_argument(
    "--inodes",
    action="store_true",
    help="Print inode number of each file.",
)
group1.add_argument(
    "--device",
    action="store_true",
    help="Print device ID number to which each file belongs.",
)
group2 = parser.add_argument_group("  ------- Sorting options -------")
group2.add_argument(
    "-v",
    action="store_true",
    help="Sort files alphanumerically by version.",
)
group2.add_argument(
    "-t",
    action="store_true",
    help="Sort files by last modification time.",
)
group2.add_argument(
    "-c",
    action="store_true",
    help="Sort files by last status change time.",
)
group2.add_argument(
    "-U",
    action="store_true",
    help="Leave files unsorted.",
)
group2.add_argument(
    "-r",
    action="store_true",
    help="Reverse the order of the sort.",
)
group2.add_argument(
    "--dirsfirst",
    action="store_true",
    help="List directories before files (-U disables).",
)
group2.add_argument(
    "--sort",
    action="store",
    metavar="X",
    type=str,
    help="Select sort: name,version,size,mtime,ctime.",
)
group3 = parser.add_argument_group("  ------- Graphics options -------")
group3.add_argument(
    "-i",
    action="store_true",
    help="Don't print indentation lines.",
)
group3.add_argument(
    "-A",
    action="store_true",
    help="ANSI lines graphic indentation lines.",
)
group3.add_argument(
    "-S",
    action="store_true",
    help="Print with CP437 (console) graphics indentation lines.",
)
group3.add_argument(
    "-n",
    action="store_true",
    help="Turn colorization off always (-C overrides).",
)
group3.add_argument(
    "-C",
    action="store_true",
    help="Turn colorization on always.",
)
group4 = parser.add_argument_group("  ------- Miscellaneous options -------")
group4.add_argument(
    "--version",
    action="version",
    help="Print version and exit.",
)
group4.add_argument(
    "--help",
    action="help",
    help="Print usage and this help message and exit.",
)
group4.add_argument(
    "--",
    action="store_true",
    dest="__terminator",
    help="Options processing terminator.",
)
parser.add_argument(
    "paths",
    type=Path,
    action="store",
    nargs='*',
    metavar="<directory list>",
)
