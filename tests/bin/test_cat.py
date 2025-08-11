import fileinput
import io

import pytest

from bin.cat import filter_non_printable, main


# Mock argparse for testing the main function
class MockNamespace:
    def __init__(self, files):
        self.files = files


class MockArgumentParser:
    def __init__(self, description):
        pass

    def add_argument(self, *args, **kwargs):
        pass

    def parse_args(self, args):
        return MockNamespace(args)


# We use the real argparse, but the above is an example of how you might mock it if needed.

# --- Unit tests for filter_non_printable function ---
def test_filter_non_printable_normal_string():
    """Test that a normal string remains unchanged."""
    test_str = "Hello, World! 123"
    assert filter_non_printable(test_str) == test_str


def test_filter_non_printable_with_control_chars():
    """Test that non-printable characters are replaced with spaces."""
    test_str = "abc\x01\x02\x03def"
    expected_str = "abc   def"
    assert filter_non_printable(test_str) == expected_str


def test_filter_non_printable_empty_string():
    """Test that an empty string returns an empty string."""
    assert filter_non_printable("") == ""


def test_filter_non_printable_only_control_chars():
    """Test a string containing only non-printable characters."""
    test_str = "\x01\x02\x03\x04"
    expected_str = "    "
    assert filter_non_printable(test_str) == expected_str


# --- Integration tests for the main function ---
def test_main_single_file(tmp_path, capsys):
    """Test the script with a single file containing non-printable chars."""
    content = "This is a test line with a non-printable char \x01.\nAnother line."
    expected_output = "This is a test line with a non-printable char  .\nAnother line."
    file_path = tmp_path / "test_file.txt"
    file_path.write_text(content, encoding="utf-8")

    with pytest.raises(SystemExit) as excinfo:
        main([str(file_path)])

    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert captured.out == expected_output
    assert captured.err == ""


def test_main_multiple_files(tmp_path, capsys):
    """Test the script with multiple files."""
    file1_content = "File 1\nwith a null byte\x00.\n"
    file2_content = "File 2\nwith a control char\x02."
    expected_output = "File 1\nwith a null byte .\nFile 2\nwith a control char ."

    file1_path = tmp_path / "file1.txt"
    file2_path = tmp_path / "file2.txt"

    file1_path.write_text(file1_content, encoding="utf-8")
    file2_path.write_text(file2_content, encoding="utf-8")

    with pytest.raises(SystemExit) as excinfo:
        main([str(file1_path), str(file2_path)])

    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert captured.out == expected_output
    assert captured.err == ""


def test_main_empty_file(tmp_path, capsys):
    """Test the script with an empty file."""
    file_path = tmp_path / "empty_file.txt"
    file_path.write_text("", encoding="utf-8")

    with pytest.raises(SystemExit) as excinfo:
        main([str(file_path)])

    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_main_stdin(capsys, monkeypatch):
    """Test the script when reading from standard input."""
    test_input = "Hello \x03world\nThis is a second line."
    expected_output = "Hello  world\nThis is a second line."
    monkeypatch.setattr('sys.stdin', io.StringIO(test_input))

    with pytest.raises(SystemExit) as excinfo:
        main([])  # No files passed, so it reads from stdin

    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert captured.out == expected_output
    assert captured.err == ""


def test_main_non_existent_file(capsys):
    """Test that the script handles a non-existent file gracefully."""
    with pytest.raises(SystemExit) as excinfo:
        main(["non_existent_file.txt"])

    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "[Errno 2] No such file or directory" in captured.err


def test_main_keyboard_interrupt(capsys, monkeypatch):
    """Test the script's graceful exit on a KeyboardInterrupt."""

    # We mock the fileinput.input function to raise the exception immediately.
    def mock_input(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(fileinput, 'input', mock_input)

    with pytest.raises(SystemExit) as excinfo:
        main(["some_file.txt"])

    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "Operation interrupted by user." in captured.err


def test_main_general_exception(capsys, monkeypatch):
    """Test the script's error handling for a generic exception."""

    def mock_input(*args, **kwargs):
        raise ValueError("A simulated error")

    monkeypatch.setattr(fileinput, 'input', mock_input)

    with pytest.raises(SystemExit) as excinfo:
        main(["some_file.txt"])

    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "cat: error: A simulated error" in captured.err
