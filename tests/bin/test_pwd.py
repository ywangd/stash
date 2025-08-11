import pytest
import sys
import os
from unittest.mock import patch, Mock
from bin.pwd import main

# A constant to use as our mocked current working directory
MOCKED_CWD = "/Users/testuser/documents/project"


@pytest.fixture(autouse=True)
def mock_cwd(monkeypatch):
    """
    This fixture mocks the os.getcwd function for all tests
    to ensure a consistent test environment.
    """
    monkeypatch.setattr(os, "getcwd", lambda: MOCKED_CWD)


@pytest.fixture
def mock_sys_exit(monkeypatch):
    """
    This fixture mocks sys.exit to prevent the main function from
    exiting the test runner.
    """
    mock_exit = Mock()
    monkeypatch.setattr(sys, "exit", mock_exit)
    return mock_exit


@pytest.fixture
def mock_collapseuser():
    """
    Mocks the collapseuser function from the original script's context.
    """

    # Create a mock for the collapseuser function
    def mock_func(path):
        return path.replace("/Users/testuser", "~")

    return mock_func


def run_main_with_args(args):
    """
    A helper function to set sys.argv and call main(),
    simulating how the script would be called via exec().
    """
    with patch.object(sys, 'argv', ['pwd.py'] + args):
        main(sys.argv[1:])


def test_main_default(capsys, mock_sys_exit, mock_collapseuser):
    """Test the main function with no arguments (default behavior)."""
    with patch('bin.pwd.collapseuser', new=mock_collapseuser):
        run_main_with_args([])

    # We expect the script to call sys.exit(0) for a successful run.
    mock_sys_exit.assert_called_with(0)

    captured = capsys.readouterr()
    assert captured.out.strip() == "~/documents/project"
    assert captured.err == ""


def test_main_fullname(capsys, mock_sys_exit):
    """Test the main function with the --fullname flag."""
    run_main_with_args(["-f"])

    mock_sys_exit.assert_called_with(0)

    captured = capsys.readouterr()
    assert captured.out.strip() == MOCKED_CWD
    assert captured.err == ""


def test_main_basename(capsys, mock_sys_exit):
    """Test the main function with the --basename flag."""
    run_main_with_args(["-b"])

    mock_sys_exit.assert_called_with(0)

    captured = capsys.readouterr()
    assert captured.out.strip() == "project"
    assert captured.err == ""


def test_main_keyboard_interrupt(capsys, mock_sys_exit):
    """Test that the main function handles KeyboardInterrupt gracefully."""
    with patch('os.getcwd', side_effect=KeyboardInterrupt):
        run_main_with_args([])

    # We expect the script to call sys.exit(1) on an interrupt.
    mock_sys_exit.assert_called_with(1)

    captured = capsys.readouterr()
    assert "Operation interrupted by user." in captured.err


def test_main_unknown_exception(capsys, mock_sys_exit):
    """Test that the main function handles an unknown exception."""
    with patch('os.getcwd', side_effect=ValueError("Something went wrong")):
        run_main_with_args([])

    # We expect the script to call sys.exit(1) on an error.
    mock_sys_exit.assert_called_with(1)

    captured = capsys.readouterr()
    assert "pwd: ValueError: Something went wrong" in captured.err
