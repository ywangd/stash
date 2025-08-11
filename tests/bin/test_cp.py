import shutil
from pathlib import Path

import pytest
from bin.cp import main, _home_relative_path


# Mock argparse for testing the main function
class MockNamespace:
    def __init__(self, source, dest):
        self.source = source
        self.dest = dest

class MockArgumentParser:
    def __init__(self, description):
        pass
    def add_argument(self, *args, **kwargs):
        pass
    def parse_args(self, args):
        # A simple parser for this test
        return MockNamespace(args[:-1], args[-1])


# --- Unit tests for _home_relative_path helper function ---
def test_home_relative_path_inside_home(monkeypatch, tmp_path):
    """Test that a path inside the mock HOME directory is made relative."""
    home_dir = tmp_path / "home_user"
    home_dir.mkdir()
    target_path = home_dir / "Documents" / "test_file.txt"
    target_path.parent.mkdir()
    monkeypatch.setenv("HOME", str(home_dir))

    # The function should be able to create a relative path
    relative_path = _home_relative_path(target_path)
    assert relative_path == Path("Documents/test_file.txt")


def test_home_relative_path_outside_home(monkeypatch, tmp_path):
    """Test that a path outside the mock HOME directory remains unchanged."""
    home_dir = tmp_path / "home_user"
    home_dir.mkdir()
    target_path = tmp_path / "other_dir" / "test_file.txt"
    target_path.parent.mkdir()
    monkeypatch.setenv("HOME", str(home_dir))

    # The function should return the original path
    relative_path = _home_relative_path(target_path)
    assert relative_path == target_path


# --- Integration tests for the main function ---
def test_main_copy_single_file_to_file(tmp_path, capsys):
    """Test copying a single file to a new file destination."""
    source_file = tmp_path / "source.txt"
    source_file.write_text("Hello, World!")
    dest_file = tmp_path / "dest.txt"

    with pytest.raises(SystemExit) as excinfo:
        main([str(source_file), str(dest_file)])

    assert excinfo.value.code == 0
    assert dest_file.exists()
    assert dest_file.read_text() == "Hello, World!"
    assert capsys.readouterr().err == ""

def test_main_copy_single_file_to_existing_dir(tmp_path, capsys):
    """Test copying a single file into an existing directory."""
    source_file = tmp_path / "source.txt"
    source_file.write_text("Test content")
    dest_dir = tmp_path / "dest_dir"
    dest_dir.mkdir()

    with pytest.raises(SystemExit) as excinfo:
        main([str(source_file), str(dest_dir)])

    assert excinfo.value.code == 0
    copied_file = dest_dir / "source.txt"
    assert copied_file.exists()
    assert copied_file.read_text() == "Test content"

def test_main_copy_single_directory(tmp_path, capsys):
    """Test copying an entire directory with contents."""
    source_dir = tmp_path / "source_dir"
    source_dir.mkdir()
    (source_dir / "file1.txt").write_text("File 1 content")
    (source_dir / "sub_dir").mkdir()
    (source_dir / "sub_dir" / "file2.txt").write_text("File 2 content")

    dest_dir = tmp_path / "dest_dir"

    with pytest.raises(SystemExit) as excinfo:
        main([str(source_dir), str(dest_dir)])

    assert excinfo.value.code == 0
    assert dest_dir.exists()
    assert (dest_dir / "file1.txt").exists()
    assert (dest_dir / "sub_dir" / "file2.txt").exists()

def test_main_copy_multiple_files_to_existing_dir(tmp_path, capsys):
    """Test copying multiple files into an existing directory."""
    source1 = tmp_path / "file1.txt"
    source1.write_text("content1")
    source2 = tmp_path / "file2.txt"
    source2.write_text("content2")
    dest_dir = tmp_path / "dest_dir"
    dest_dir.mkdir()

    with pytest.raises(SystemExit) as excinfo:
        main([str(source1), str(source2), str(dest_dir)])

    assert excinfo.value.code == 0
    assert (dest_dir / "file1.txt").exists()
    assert (dest_dir / "file2.txt").exists()
    assert (dest_dir / "file1.txt").read_text() == "content1"
    assert (dest_dir / "file2.txt").read_text() == "content2"

def test_main_multiple_sources_to_non_directory_dest(tmp_path, capsys):
    """Test failure when multiple sources are given and dest is not a directory."""
    source1 = tmp_path / "file1.txt"
    source1.touch()
    source2 = tmp_path / "file2.txt"
    source2.touch()
    dest_file = tmp_path / "dest_file.txt"
    dest_file.touch()

    with pytest.raises(SystemExit) as excinfo:
        main([str(source1), str(source2), str(dest_file)])

    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert f"cp: target '{_home_relative_path(dest_file)}' is not a directory" in captured.err

def test_main_non_existent_source(tmp_path, capsys):
    """Test failure when a source file does not exist."""
    non_existent = tmp_path / "non_existent.txt"
    dest_dir = tmp_path / "dest_dir"
    dest_dir.mkdir()

    with pytest.raises(SystemExit) as excinfo:
        main([str(non_existent), str(dest_dir)])

    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert f"cp: {_home_relative_path(non_existent)}: No such file or directory" in captured.err

def test_main_copy_file_onto_itself(monkeypatch, tmp_path, capsys):
    """Test failure when trying to copy a file onto itself by mocking shutil.copy to raise an error."""
    source_file = tmp_path / "file.txt"
    source_file.touch()

    def mock_copy_error(src, dest):
        # We raise shutil.SameFileError explicitly to ensure the exception is raised
        # regardless of the underlying system's behavior.
        raise shutil.SameFileError(f"'{src}' and '{dest}' are the same file")

    # Use monkeypatch to replace the real shutil.copy with our mock function
    monkeypatch.setattr(shutil, 'copy', mock_copy_error)

    with pytest.raises(SystemExit) as excinfo:
        main([str(source_file), str(source_file)])

    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert f"cp: {_home_relative_path(source_file)}: '{source_file}' and '{source_file}' are the same file" in captured.err

def test_main_keyboard_interrupt(monkeypatch, tmp_path, capsys):
    """Test that the script handles a KeyboardInterrupt gracefully."""
    source_file = tmp_path / "source.txt"
    source_file.touch()
    dest_file = tmp_path / "dest.txt"

    def mock_copy(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(shutil, 'copy', mock_copy)

    with pytest.raises(SystemExit) as excinfo:
        main([str(source_file), str(dest_file)])

    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "\ncp: Operation interrupted by user." in captured.err

def test_main_shutil_error(monkeypatch, tmp_path, capsys):
    """Test that the script handles a generic shutil.Error."""
    source_file = tmp_path / "source.txt"
    source_file.touch()
    dest_file = tmp_path / "dest.txt"

    def mock_copy(*args, **kwargs):
        raise shutil.Error("Simulated shutil error")

    monkeypatch.setattr(shutil, 'copy', mock_copy)

    with pytest.raises(SystemExit) as excinfo:
        main([str(source_file), str(dest_file)])

    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert f"cp: {_home_relative_path(source_file)}: Simulated shutil error" in captured.err
