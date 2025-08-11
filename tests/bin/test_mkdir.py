import pytest
import sys
import os
import shutil
from unittest.mock import patch, Mock
from pathlib import Path
from bin.mkdir import main

# A constant to use as our mocked temporary directory for tests
MOCKED_TMP_DIR = Path("/tmp/test_dir_mkdir")


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """
    Sets up a temporary directory structure for testing.
    """
    if MOCKED_TMP_DIR.exists():
        shutil.rmtree(MOCKED_TMP_DIR)
    os.makedirs(MOCKED_TMP_DIR, exist_ok=True)

    yield

    # Clean up the directory after the test
    if MOCKED_TMP_DIR.exists():
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
    with patch.object(sys, 'argv', ['mkdir.py'] + args):
        main(sys.argv[1:])


def test_mkdir_single_directory(setup_test_environment):
    """Test creating a single new directory."""
    dir_to_create = MOCKED_TMP_DIR / "new_dir"
    assert not dir_to_create.exists()

    with pytest.raises(SystemExit) as excinfo:
        run_main_with_args([str(dir_to_create)])

    assert excinfo.value.code == 0
    assert dir_to_create.exists()
    assert dir_to_create.is_dir()


def test_mkdir_multiple_directories(setup_test_environment):
    """Test creating multiple directories at once."""
    dir1 = MOCKED_TMP_DIR / "dir1"
    dir2 = MOCKED_TMP_DIR / "dir2"

    assert not dir1.exists()
    assert not dir2.exists()

    with pytest.raises(SystemExit) as excinfo:
        run_main_with_args([str(dir1), str(dir2)])

    assert excinfo.value.code == 0
    assert dir1.exists() and dir1.is_dir()
    assert dir2.exists() and dir2.is_dir()


def test_mkdir_directory_with_parents(setup_test_environment):
    """Test creating a directory with its parents using -p flag."""
    dir_to_create = MOCKED_TMP_DIR / "parent" / "child"
    assert not dir_to_create.exists()

    with pytest.raises(SystemExit) as excinfo:
        run_main_with_args(["-p", str(dir_to_create)])

    assert excinfo.value.code == 0
    assert dir_to_create.exists()
    assert dir_to_create.is_dir()


def test_mkdir_existing_directory(capsys, setup_test_environment):
    """Test creating a directory that already exists."""
    existing_dir = MOCKED_TMP_DIR / "existing_dir"
    os.mkdir(existing_dir)

    with pytest.raises(SystemExit) as excinfo:
        run_main_with_args([str(existing_dir)])

    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "mkdir: FileExistsError" in captured.err


def test_mkdir_without_parents_when_needed(capsys, setup_test_environment):
    """Test creating a nested directory without the -p flag."""
    dir_to_create = MOCKED_TMP_DIR / "non_existent_parent" / "child"

    with pytest.raises(SystemExit) as excinfo:
        run_main_with_args([str(dir_to_create)])

    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "mkdir: FileNotFoundError" in captured.err or "The system cannot find the path specified" in captured.err
    assert not dir_to_create.exists()


def test_mkdir_keyboard_interrupt(capsys, monkeypatch, mock_sys_exit):
    """Test that the main function handles a KeyboardInterrupt gracefully."""

    # Mock os.mkdir to raise a KeyboardInterrupt
    def mock_mkdir(path, mode=0o777):
        raise KeyboardInterrupt

    monkeypatch.setattr('os.mkdir', mock_mkdir)

    run_main_with_args([str(MOCKED_TMP_DIR / "some_dir")])

    mock_sys_exit.assert_called_with(1)
    captured = capsys.readouterr()
    assert "Operation interrupted by user." in captured.err
