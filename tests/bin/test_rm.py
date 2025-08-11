import pytest
import sys
import os
import shutil
from unittest.mock import patch, Mock
from pathlib import Path
from bin.rm import main, rm

# A constant to use as our mocked temporary directory for tests
MOCKED_TMP_DIR = Path("/tmp/test_dir_rm")


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """
    Sets up a temporary directory structure for testing and patches
    the environment to use it.
    """
    # Create the temporary directory and subdirectories
    os.makedirs(MOCKED_TMP_DIR / "subdir" / "nested", exist_ok=True)
    (MOCKED_TMP_DIR / "file1.txt").touch()
    (MOCKED_TMP_DIR / "subdir" / "file2.txt").touch()

    # Patch os.chdir to prevent tests from changing the real current directory
    # Although rm doesn't use chdir, it's good practice for general test isolation
    mock_chdir = Mock()
    monkeypatch.setattr(os, "chdir", mock_chdir)

    # Patch Path.cwd() to return our mocked temporary directory for consistency
    monkeypatch.setattr(Path, "cwd", lambda: MOCKED_TMP_DIR)

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
    with patch.object(sys, 'argv', ['rm.py'] + args):
        main(sys.argv[1:])


def test_rm_file(setup_test_environment):
    """Test removing a single file."""
    file_to_remove = MOCKED_TMP_DIR / "file1.txt"
    assert file_to_remove.exists()
    run_main_with_args([str(file_to_remove)])
    assert not file_to_remove.exists()


def test_rm_non_existent_file_no_force(capsys, setup_test_environment):
    """Test removing a non-existent file without the --force flag."""
    non_existent_file = MOCKED_TMP_DIR / "non_existent.txt"
    run_main_with_args([str(non_existent_file)])

    captured = capsys.readouterr()
    assert f"rm: {non_existent_file}: No such file or directory" in captured.err


def test_rm_non_existent_file_with_force(capsys, setup_test_environment):
    """Test removing a non-existent file with the --force flag."""
    non_existent_file = MOCKED_TMP_DIR / "non_existent.txt"
    run_main_with_args(["-f", str(non_existent_file)])

    captured = capsys.readouterr()
    assert captured.err == ""


def test_rm_directory_without_recursive(capsys, setup_test_environment):
    """Test trying to remove a directory without the --recursive flag."""
    dir_to_remove = MOCKED_TMP_DIR / "subdir"
    assert dir_to_remove.exists()
    run_main_with_args([str(dir_to_remove)])

    captured = capsys.readouterr()
    assert f"rm: {dir_to_remove}: Is a directory" in captured.err
    assert dir_to_remove.exists()


def test_rm_directory_with_recursive(setup_test_environment):
    """Test removing a directory with contents recursively."""
    dir_to_remove = MOCKED_TMP_DIR / "subdir"
    assert dir_to_remove.exists()
    run_main_with_args(["-r", str(dir_to_remove)])
    assert not dir_to_remove.exists()


def test_rm_interactive_file_yes(capsys, setup_test_environment):
    """Test interactive removal of a file with a 'y' response."""
    file_to_remove = MOCKED_TMP_DIR / "file1.txt"
    assert file_to_remove.exists()
    with patch('builtins.input', return_value='y'):
        run_main_with_args(["-i", str(file_to_remove)])
    assert not file_to_remove.exists()


def test_rm_interactive_file_no(capsys, setup_test_environment):
    """Test interactive removal of a file with a 'n' response."""
    file_to_remove = MOCKED_TMP_DIR / "file1.txt"
    assert file_to_remove.exists()
    with patch('builtins.input', return_value='n'):
        run_main_with_args(["-i", str(file_to_remove)])
    assert file_to_remove.exists()


def test_rm_interactive_recursive_directory_yes(capsys, setup_test_environment):
    """Test interactive recursive removal of a directory with a 'y' response."""
    dir_to_remove = MOCKED_TMP_DIR / "subdir"
    assert dir_to_remove.exists()
    with patch('builtins.input', return_value='y'):
        run_main_with_args(["-r", "-i", str(dir_to_remove)])
    assert not dir_to_remove.exists()


def test_rm_interactive_recursive_directory_no(capsys, setup_test_environment):
    """Test interactive recursive removal of a directory with a 'n' response."""
    dir_to_remove = MOCKED_TMP_DIR / "subdir"
    assert dir_to_remove.exists()
    with patch('builtins.input', return_value='n'):
        run_main_with_args(["-r", "-i", str(dir_to_remove)])
    assert dir_to_remove.exists()


def test_rm_verbose_file(capsys, setup_test_environment):
    """Test removing a file with the --verbose flag."""
    file_to_remove = MOCKED_TMP_DIR / "file1.txt"
    run_main_with_args(["-v", str(file_to_remove)])
    captured = capsys.readouterr()
    assert f"removed '{file_to_remove}'" in captured.out


def test_rm_verbose_directory(capsys, setup_test_environment):
    """Test removing a directory with the --verbose and --recursive flags."""
    dir_to_remove = MOCKED_TMP_DIR / "subdir"
    run_main_with_args(["-r", "-v", str(dir_to_remove)])
    captured = capsys.readouterr()
    assert f"removed directory '{dir_to_remove}'" in captured.out


def test_rm_keyboard_interrupt(capsys, monkeypatch, mock_sys_exit):
    """Test that the main function handles a KeyboardInterrupt gracefully."""

    # Mock the rm function to raise a KeyboardInterrupt
    def mock_rm_interrupt(path, args):
        raise KeyboardInterrupt

    monkeypatch.setattr('bin.rm.rm', mock_rm_interrupt)

    run_main_with_args([str(MOCKED_TMP_DIR / "file1.txt")])

    mock_sys_exit.assert_called_with(1)
    captured = capsys.readouterr()
    assert "Operation interrupted by user." in captured.err
