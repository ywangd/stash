"""
Script to generate `tree_parser.py` from `_tree_help.sh`
"""

import re
from pathlib import Path

__version__ = "0.1.0"

with open(Path(__file__).parent / "_tree_help.sh") as fp:
    ff = fp.read()


optp = """group{group}.add_argument(
    "{flag}",
    action="store",
    metavar="{metavar}",
    type={type},
    help="{help}",
)"""
flagp = """group{group}.add_argument(
    "{flag}",
    action="store_true",
    help="{help}",
)"""
special_flagp = """group{group}.add_argument(
    "{flag}",
    action="store_true",
    dest="{dest}",
    help="{help}",
)"""
spec_action_flag = """group{group}.add_argument(
    "{flag}",
    action="{action}",
    help="{help}",
)"""
positional = """parser.add_argument(
    "paths",
    type=Path,
    action="store",
    nargs='*',
    metavar="<directory list>",
)"""


known_arg_types = {
    "-L": "int",
    "-P": "str",
    "-I": "str",
    "--charset": "str",
    "--filelimit": "int",
    "--timefmt": "str",
    "-o": "Path",
    "--sort": "str",
    "-H": "str",
    "-T": "str",
}
known_arg_dests = {"--": "__terminator"}
# section = r'^  ----.+$'
# lookup = r'^  (--*\w[-\w]{0,})\s([<>\w#]*)\s+([A-Z].+)$'

section = r"^  ----.+$"
lookup_with_metavar = r"^  (--*\w[-\w]*)\s+([<>\w#]+)\s+([A-Z].+)$"
lookup_without_metavar = r"^  (--*[-\w]+)\s+([A-Z].+)$"
special_lookup = r"^  (--+)\s+([A-Z].+)$"


g = 0
lines = []
lines.append("import argparse")
lines.append("from pathlib import Path")
lines.append(f"\n__version__ = '{__version__}'")
lines.append("\n__all__ = ('parser',)")
lines.append("\n")
lines.append("parser = argparse.ArgumentParser(description=__doc__, add_help=False)")
lines.append("parser.version = __version__")
for i, line in enumerate(ff.split("\n")):
    if re.search(section, line):
        lines.append(f'group{g} = parser.add_argument_group("{line}")')
        g += 1
    elif re.search(special_lookup, line):
        flag = re.search(special_lookup, line).group(1)
        dest = known_arg_dests[flag]
        lines.append(
            special_flagp.format(
                group=g - 1,
                flag=flag.strip(),
                dest=dest,
                help="Options processing terminator.",
            )
        )
    else:
        m = re.search(lookup_with_metavar, line)
        if m:
            gr = m.groups()
            flag, metavar, help_ = gr
            flag = flag.strip()
            metavar = metavar.strip()
            help_ = help_.strip()
            if flag in known_arg_types:
                type_ = known_arg_types[flag]
                lines.append(
                    optp.format(
                        group=g - 1, flag=flag, metavar=metavar, type=type_, help=help_
                    )
                )
            else:
                lines.append(flagp.format(group=g - 1, flag=flag, help=help_))
        else:
            m = re.search(lookup_without_metavar, line)
            if m:
                gr = m.groups()
                flag, help_ = gr
                if flag == "--help":
                    lines.append(
                        spec_action_flag.format(
                            group=g - 1,
                            action="help",
                            flag=flag.strip(),
                            help=help_.strip(),
                        )
                    )
                elif flag == "--version":
                    lines.append(
                        spec_action_flag.format(
                            group=g - 1,
                            action="version",
                            flag=flag.strip(),
                            help=help_.strip(),
                        )
                    )
                else:
                    lines.append(
                        flagp.format(group=g - 1, flag=flag.strip(), help=help_.strip())
                    )

lines.append(positional)
lines.append("\n")
# lines.append("ns = parser.parse_args()")
# lines.append("print(ns)")
with open(Path(__file__).parent / "tree_parser.py", "w") as fp:
    fp.write("\n".join(lines))
