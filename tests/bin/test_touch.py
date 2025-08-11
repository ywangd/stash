import sys
from pathlib import Path
from unittest.mock import patch, mock_open

import pytest
# Assuming the touch.py file is in the same directory for this test
from bin.touch import main


# Fixture to track calls to sys.exit and their exit codes
@pytest.fixture
def mock_exit_code(monkeypatch):
    """Mocks sys.exit to track the exit code without exiting the test."""
    exit_code = [None]

    def exit_mock(code):
        exit_code[0] = code

    monkeypatch.setattr(sys, "exit", exit_mock)
    return exit_code


def test_create_new_file_when_not_exist(monkeypatch, mock_exit_code):
    """Tests that the script creates a new file if it doesn't exist."""
    filename = "new_file.txt"
    monkeypatch.setattr(sys, 'argv', ['touch.py', filename])

    # Mock pathlib.Path.exists() to return False
    with patch('pathlib.Path.exists', return_value=False), \
            patch('builtins.open', mock_open()) as mocked_file_open, \
            patch('os.utime') as mocked_utime:
        main(sys.argv[1:])

        # The script should exit with a code of 0 on success.
        assert mock_exit_code[0] == 0

        # Verify that open was called to create the file
        mocked_file_open.assert_called_once_with(Path(filename), "wb")

        # Verify that os.utime was called to update the time
        mocked_utime.assert_called_once_with(Path(filename), None)


def test_update_existing_file_mtime(monkeypatch, mock_exit_code):
    """Tests that the script updates the modification time of an existing file."""
    filename = "existing_file.txt"
    monkeypatch.setattr(sys, 'argv', ['touch.py', filename])

    # Mock pathlib.Path.exists() to return True
    with patch('pathlib.Path.exists', return_value=True), \
            patch('builtins.open', mock_open()) as mocked_file_open, \
            patch('os.utime') as mocked_utime:
        main(sys.argv[1:])

        # The script should exit with a code of 0 on success.
        assert mock_exit_code[0] == 0

        # Verify that open was NOT called, as the file already exists
        mocked_file_open.assert_not_called()

        # Verify that os.utime was called to update the time
        mocked_utime.assert_called_once_with(Path(filename), None)


def test_no_create_flag_prevents_file_creation_with_error(capsys, monkeypatch):
    """Tests that the -c flag prevents the creation of a non-existent file and raises an exception."""
    filename = "non_existent.txt"
    monkeypatch.setattr(sys, 'argv', ['touch.py', '-c', filename])

    with patch('pathlib.Path.exists', return_value=False), \
            patch('builtins.open', mock_open()) as mocked_file_open, \
            patch('os.utime', side_effect=FileNotFoundError):
        with pytest.raises(SystemExit) as e:
            main(sys.argv[1:])

        # The script's `os.utime` call will fail and trigger an exception, causing it to exit with code 1.
        assert e.value.code == 1

        # Verify that open was NOT called
        mocked_file_open.assert_not_called()

        captured = capsys.readouterr()
        # Verify that the correct error message is printed to stderr.
        assert "touch: FileNotFoundError: " in captured.err


def test_multiple_files_are_processed(monkeypatch, mock_exit_code):
    """Tests that the script handles multiple file arguments correctly."""
    files_to_touch = ["file1.txt", "file2.txt", "file3.txt"]
    monkeypatch.setattr(sys, 'argv', ['touch.py'] + files_to_touch)

    with patch('pathlib.Path.exists', side_effect=[False, True, False]), \
            patch('builtins.open', mock_open()) as mocked_file_open, \
            patch('os.utime') as mocked_utime:
        main(sys.argv[1:])

        # The script should exit with a code of 0 on success.
        assert mock_exit_code[0] == 0

        # Verify that open was called for the two non-existent files
        assert mocked_file_open.call_count == 2

        # Verify that os.utime was called for all three files
        assert mocked_utime.call_count == 3


def test_keyboard_interrupt_exits_with_error(capsys, monkeypatch):
    """Tests the handling of a KeyboardInterrupt."""
    monkeypatch.setattr(sys, 'argv', ['touch.py', 'file.txt'])

    # Mock a function inside the try block to raise the exception
    with patch('pathlib.Path.exists', return_value=True), \
            patch('os.utime', side_effect=KeyboardInterrupt):
        with pytest.raises(SystemExit) as e:
            main(sys.argv[1:])

        # The script should exit with a code of 1.
        assert e.value.code == 1

        captured = capsys.readouterr()
        # Verify the correct error message is printed to stderr.
        assert captured.err.strip() == "Operation interrupted by user."


def test_general_exception_exits_with_error(capsys, monkeypatch):
    """Tests that the script handles a general exception."""
    filename = "file.txt"
    monkeypatch.setattr(sys, 'argv', ['touch.py', filename])

    with patch('pathlib.Path.exists', return_value=True), \
            patch('os.utime', side_effect=Exception("Test Exception")):
        with pytest.raises(SystemExit) as e:
            main(sys.argv[1:])

        # The script should exit with a code of 1.
        assert e.value.code == 1

        captured = capsys.readouterr()
        # Verify that the correct error message is printed to stderr.
        assert "touch: Exception: Test Exception" in captured.err
