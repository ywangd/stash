import pytest
import sys
import os
import shutil
from unittest.mock import patch, Mock
from pathlib import Path
from bin.rmdir import main, rmdir

# A constant to use as our mocked temporary directory for tests
MOCKED_TMP_DIR = Path("/tmp/test_dir_rmdir")


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """
    Sets up a temporary directory structure for testing and patches
    the environment to use it.
    """
    # Create the temporary directory and an empty subdirectory
    os.makedirs(MOCKED_TMP_DIR / "empty_dir", exist_ok=True)

    # Create a non-empty directory for a negative test case
    os.makedirs(MOCKED_TMP_DIR / "non_empty_dir", exist_ok=True)
    (MOCKED_TMP_DIR / "non_empty_dir" / "file.txt").touch()

    # Patch os.chdir, though not used by the script, for consistency
    mock_chdir = Mock()
    monkeypatch.setattr(os, "chdir", mock_chdir)

    yield

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
    with patch.object(sys, 'argv', ['rmdir.py'] + args):
        main(sys.argv[1:])


def test_rmdir_empty_directory(capsys, setup_test_environment):
    """Test removing a single empty directory successfully."""
    dir_to_remove = MOCKED_TMP_DIR / "empty_dir"
    assert dir_to_remove.exists()
    run_main_with_args([str(dir_to_remove)])
    assert not dir_to_remove.exists()
    captured = capsys.readouterr()
    assert captured.err == ""


def test_rmdir_non_empty_directory(capsys, setup_test_environment):
    """Test trying to remove a non-empty directory."""
    dir_to_remove = MOCKED_TMP_DIR / "non_empty_dir"
    assert dir_to_remove.exists()
    run_main_with_args([str(dir_to_remove)])

    captured = capsys.readouterr()
    assert "rmdir: failed to remove" in captured.err
    assert dir_to_remove.exists()


def test_rmdir_non_existent_directory(capsys, setup_test_environment):
    """Test trying to remove a non-existent directory."""
    non_existent_dir = MOCKED_TMP_DIR / "non_existent_dir"
    run_main_with_args([str(non_existent_dir)])

    captured = capsys.readouterr()
    assert "rmdir: failed to remove" in captured.err
    # The error message depends on the OS, so we check for either possibility
    assert "No such file or directory" in captured.err or "The system cannot find the file specified" in captured.err


def test_rmdir_verbose_flag(capsys, setup_test_environment):
    """Test removing an empty directory with the --verbose flag."""
    dir_to_remove = MOCKED_TMP_DIR / "empty_dir"
    assert dir_to_remove.exists()
    run_main_with_args(["-v", str(dir_to_remove)])
    assert not dir_to_remove.exists()

    captured = capsys.readouterr()
    assert f"Removed directory '{dir_to_remove}'" in captured.out
    assert captured.err == ""


def test_rmdir_multiple_directories(setup_test_environment):
    """Test removing multiple empty directories at once."""
    dir1 = MOCKED_TMP_DIR / "empty_dir"
    dir2 = MOCKED_TMP_DIR / "another_empty_dir"
    os.makedirs(dir2)

    assert dir1.exists()
    assert dir2.exists()

    run_main_with_args([str(dir1), str(dir2)])
    assert not dir1.exists()
    assert not dir2.exists()


def test_rmdir_keyboard_interrupt(capsys, monkeypatch, mock_sys_exit):
    """Test that the main function handles a KeyboardInterrupt gracefully."""

    # Mock the rmdir function to raise a KeyboardInterrupt
    def mock_rmdir_interrupt(paths, verbose):
        raise KeyboardInterrupt

    monkeypatch.setattr('bin.rmdir.rmdir', mock_rmdir_interrupt)

    run_main_with_args([str(MOCKED_TMP_DIR / "empty_dir")])

    mock_sys_exit.assert_called_with(1)
    captured = capsys.readouterr()
    assert "Operation interrupted by user." in captured.err
