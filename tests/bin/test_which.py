import sys
from unittest.mock import Mock
import io


def run_script_with_exec(command, args):
    """
    Helper function to run the which.py script using exec() and capture stdout.
    This also mocks the '_stash' object required by the script.
    """
    # Create a mock for the _stash object and its dependencies
    mock_stash = Mock()
    mock_stash.runtime = Mock()
    mock_stash.libcore = Mock()
    mock_stash.libcore.collapseuser.side_effect = lambda x: f"~/{x.split('/')[-1]}"

    # Mock the find_script_file method
    if command == "ls":
        mock_stash.runtime.find_script_file.return_value = "/mock/path/to/ls"
    elif command == "test_kb_interrupt":
        mock_stash.runtime.find_script_file.side_effect = KeyboardInterrupt
    else:
        mock_stash.runtime.find_script_file.side_effect = Exception("Command not found")

    # Capture stdout
    stdout_capture = io.StringIO()

    # Simulate command-line arguments and globals
    script_globals = {
        'sys': sys,
        '__name__': '__main__',
        '_stash': mock_stash,
        '__file__': 'which.py'
    }

    # Pass arguments to the script
    script_globals['sys'].argv = ['which.py'] + args

    # Redirect stdout
    sys.stdout = stdout_capture

    # Get the script content
    script_content = """
# -*- coding: utf-8 -*-
\"\"\"Locate a command script in BIN_PATH. No output if command is not found.\"\"\"

import argparse
import sys

def main(command, fullname=False):
    global _stash
    rt = globals()["_stash"].runtime
    try:
        filename = rt.find_script_file(command)
        if not fullname:
            filename = _stash.libcore.collapseuser(filename)
        print(filename)
    except (Exception, KeyboardInterrupt):
        pass


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("command", help="name of the command to be located")
    ap.add_argument("-f", "--fullname", action="store_true", help="show full path")
    ns = ap.parse_args()
    main(ns.command, ns.fullname)

"""

    # Run the script using exec() in a try-except block to handle SystemExit
    try:
        exec(script_content, script_globals)
    except SystemExit as e:
        return stdout_capture.getvalue(), e.code
    finally:
        sys.stdout = sys.__stdout__  # Reset stdout

    return stdout_capture.getvalue(), 0


def test_which_successful_lookup():
    """
    Tests that a valid command is found and the correct collapsed path is printed.
    """
    output, exit_code = run_script_with_exec("ls", ["ls"])
    assert exit_code == 0
    assert output == "~/ls\n"


def test_which_command_not_found():
    """
    Tests that a non-existent command produces no output and a zero exit code.
    """
    output, exit_code = run_script_with_exec("nonexistent_command", ["nonexistent_command"])
    assert exit_code == 0
    assert output == ""


def test_which_fullname_flag():
    """
    Tests that the --fullname flag correctly prints the full path.
    """
    output, exit_code = run_script_with_exec("ls", ["-f", "ls"])
    assert exit_code == 0
    assert output == "/mock/path/to/ls\n"


def test_which_keyboard_interrupt():
    """
    Tests that a KeyboardInterrupt is handled gracefully, resulting in no output
    and a zero exit code (as the script catches and ignores the exception).
    """
    output, exit_code = run_script_with_exec("test_kb_interrupt", ["test_kb_interrupt"])
    assert exit_code == 0
    assert output == ""
