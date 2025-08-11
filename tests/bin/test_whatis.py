import sys
from unittest.mock import patch, Mock
from bin.whatis import main


def run_main_with_args(args):
    """
    A helper function to set sys.argv and call main(),
    simulating how the script would be called from the command line.
    """
    with patch.object(sys, 'argv', ['whatis.py'] + args):
        try:
            main(sys.argv[1:])
        except SystemExit as e:
            return e.code
    return 0


def test_whatis_successful_lookup(capsys):
    """
    Tests that a valid command is found and the correct description is printed.
    """
    exit_code = run_main_with_args(['ls'])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "ls - List files\n" == captured.out


def test_whatis_command_not_found(capsys):
    """
    Tests that a non-existent command results in an error message
    and a non-zero exit code.
    """
    exit_code = run_main_with_args(['nonexistent_command'])
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "whatis: nothing appropriate\n" == captured.out


def test_whatis_no_arguments(capsys):
    """
    Tests that calling the script with no arguments prints the usage message
    and results in a non-zero exit code.
    """
    exit_code = run_main_with_args([])
    assert exit_code == 2
    captured = capsys.readouterr()
    assert "usage: whatis.py [-h] command\n" in captured.err


def test_whatis_keyboard_interrupt(capsys, monkeypatch):
    """
    Tests that the script handles a KeyboardInterrupt gracefully by
    exiting with code 1 and printing an error message.
    """
    # We patch the `json.loads` method to raise a KeyboardInterrupt.
    # This allows the script's main function to catch the exception.
    # Note: This test will only pass after the `json.loads` call in whatis.py
    # is moved inside the main `try...except` block.
    monkeypatch.setattr('json.loads', Mock(side_effect=KeyboardInterrupt))

    # We use the helper function to capture the exit code
    exit_code = run_main_with_args(['ls'])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "Operation interrupted by user." in captured.err
