import shutil

import pytest
import sys
import os
from unittest.mock import patch, Mock
from pathlib import Path
from bin.cd import main

# A constant to use as our mocked temporary directory for tests
MOCKED_TMP_DIR = Path("/tmp/test_dir")


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """
    Sets up a temporary directory structure for testing and patches
    the environment to use it.
    """
    # Create the temporary directory and subdirectories
    os.makedirs(MOCKED_TMP_DIR / "subdir", exist_ok=True)
    (MOCKED_TMP_DIR / "file.txt").touch()

    # Patch os.chdir to prevent tests from changing the real current directory
    mock_chdir = Mock()
    monkeypatch.setattr(os, "chdir", mock_chdir)

    # Patch Path.cwd() to return our mocked temporary directory for consistency
    monkeypatch.setattr(Path, "cwd", lambda: MOCKED_TMP_DIR)

    yield mock_chdir  # Yield the mock object for verification

    # Clean up the directory after the test
    if os.path.exists(MOCKED_TMP_DIR):
        shutil.rmtree(MOCKED_TMP_DIR)


@pytest.fixture
def mock_sys_exit(monkeypatch):
    """
    Mocks sys.exit to prevent the main function from
    exiting the test runner.
    """
    mock_exit = Mock()
    monkeypatch.setattr(sys, "exit", mock_exit)
    return mock_exit


def run_main_with_args(args):
    """
    A helper function to set sys.argv and call main(),
    simulating how the script would be called via exec().
    """
    with patch.object(sys, 'argv', ['cd.py'] + args):
        main(sys.argv[1:])


def test_cd_to_existing_directory(capsys, mock_sys_exit, setup_test_environment):
    """Test changing to an existing directory."""
    dir_to_change_to = MOCKED_TMP_DIR / "subdir"
    run_main_with_args([str(dir_to_change_to)])

    # Check that os.chdir was called with the correct path
    setup_test_environment.assert_called_with(dir_to_change_to)
    mock_sys_exit.assert_called_with(0)
    assert capsys.readouterr().err == ""


def test_cd_to_non_existent_directory(capsys, mock_sys_exit, setup_test_environment):
    """Test changing to a non-existent directory."""
    non_existent_dir = MOCKED_TMP_DIR / "non_existent_dir"
    run_main_with_args([str(non_existent_dir)])

    # Check that os.chdir was not called
    setup_test_environment.assert_not_called()
    mock_sys_exit.assert_called_with(1)

    captured = capsys.readouterr()
    assert f"cd: {non_existent_dir}: No such file or directory" in captured.out


def test_cd_to_a_file(capsys, mock_sys_exit, setup_test_environment):
    """Test trying to change to a file instead of a directory."""
    file_path = MOCKED_TMP_DIR / "file.txt"
    run_main_with_args([str(file_path)])

    # Check that os.chdir was not called
    setup_test_environment.assert_not_called()
    mock_sys_exit.assert_called_with(1)

    captured = capsys.readouterr()
    assert f"cd: {file_path}: Not a directory" in captured.out


def test_cd_no_arguments(capsys, mock_sys_exit, setup_test_environment):
    """Test the default behavior when no arguments are given."""
    run_main_with_args([])

    # We need to mock expanduser and HOME2_DEFAULT for this test
    home_dir = Path("~").expanduser()
    documents_dir = home_dir / "Documents"

    # The script should try to change to the default directory
    setup_test_environment.assert_called_with(documents_dir)
    mock_sys_exit.assert_called_with(0)


def test_cd_keyboard_interrupt(capsys, monkeypatch, mock_sys_exit):
    """Test that the main function handles KeyboardInterrupt gracefully."""

    # Mock os.chdir to raise a KeyboardInterrupt
    def mock_chdir_interrupt(path):
        raise KeyboardInterrupt

    monkeypatch.setattr(os, "chdir", mock_chdir_interrupt)

    run_main_with_args([str(MOCKED_TMP_DIR)])

    # We expect the script to call sys.exit(1) on an interrupt.
    mock_sys_exit.assert_called_with(1)

    captured = capsys.readouterr()
    assert "Operation interrupted by user." in captured.err


def test_cd_unknown_exception(capsys, monkeypatch, mock_sys_exit):
    """Test that the main function handles an unknown exception."""

    # Mock os.chdir to raise a generic exception
    def mock_chdir_exception(path):
        raise ValueError("Something went wrong")

    monkeypatch.setattr(os, "chdir", mock_chdir_exception)

    run_main_with_args([str(MOCKED_TMP_DIR)])

    # We expect the script to call sys.exit(1) on an error.
    mock_sys_exit.assert_called_with(1)

    captured = capsys.readouterr()
    assert "cd: ValueError: Something went wrong" in captured.err
