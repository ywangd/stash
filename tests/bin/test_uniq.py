import pytest
from io import StringIO
from unittest.mock import patch
from bin.whatis import main, file

@pytest.fixture
def run_main_with_captured_output():
    """
    Fixture to help run the main function and capture stdout and stderr.
    This fixture is specifically for tests that do not expect a SystemExit.
    """
    def _runner(args):
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
                try:
                    main(args)
                except SystemExit:
                    pass
                return mock_stdout.getvalue(), mock_stderr.getvalue()
    return _runner

def test_valid_command(run_main_with_captured_output):
    """
    Tests that a valid command returns the expected description.
    """
    stdout, stderr = run_main_with_captured_output(['ls'])
    assert stdout == "ls - List files\n"
    assert stderr == ""

def test_nonexistent_command(run_main_with_captured_output):
    """
    Tests that a nonexistent command returns the 'nothing appropriate' error.
    The script prints this to stdout before exiting.
    """
    stdout, stderr = run_main_with_captured_output(['non_existent_command'])
    assert stdout == "whatis: nothing appropriate\n"
    assert stderr == ""

def test_keyboard_interrupt_handling(run_main_with_captured_output):
    """
    Tests that KeyboardInterrupt is handled gracefully.
    """
    with patch('json.loads', side_effect=KeyboardInterrupt):
        stdout, stderr = run_main_with_captured_output(['ls'])
    assert stdout == ""
    assert "Operation interrupted by user." in stderr

def test_general_exception_handling(run_main_with_captured_output):
    """
    Tests that a general exception is handled gracefully.
    """
    with patch('json.loads', side_effect=Exception("Test exception")):
        stdout, stderr = run_main_with_captured_output(['ls'])
    assert stdout == ""
    assert "cat: error: Test exception" in stderr

def test_no_arguments_provided():
    """
    Tests that the script exits with an error when no arguments are provided.
    """
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        main([])
    assert pytest_wrapped_e.type == SystemExit

def test_too_many_arguments():
    """
    Tests that the script exits with an error when too many arguments are provided.
    """
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        main(['ls', 'cat'])
    assert pytest_wrapped_e.type == SystemExit
