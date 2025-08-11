import os
from io import StringIO
from unittest.mock import patch

import pytest
from bin.printenv import main

# Mock environment variables for testing
MOCK_ENV = {
    "HOME": "/home/user",
    "PATH": "/usr/local/bin:/usr/bin:/bin",
    "SHELL": "/bin/bash",
    "VAR_WITH_NUM_0": "zero",
    "VALID_VAR": "valid_value",
}


class MockEnviron(dict):
    """Subclass of dict so that `items` can be patched in tests."""
    pass


@pytest.fixture(autouse=True)
def mock_environ(monkeypatch):
    """
    Fixture to mock os.environ for all tests.

    Uses a dict subclass so that `items` can be patched,
    and `.copy()` to prevent pytest from injecting extra keys.
    """
    env = MockEnviron(MOCK_ENV.copy())
    monkeypatch.setattr(os, "environ", env)


@pytest.fixture
def run_main():
    """
    Fixture to help run the main function with provided arguments and capture output.
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


# Test cases
def test_all_variables_printed_when_no_args(run_main):
    """
    Tests if all valid environment variables are printed when no arguments are provided.
    """
    stdout, stderr = run_main([])
    output_lines = set(stdout.strip().split('\n'))

    # Remove pytest's injected tracking variable if present
    output_lines = {line for line in output_lines if not line.startswith("PYTEST_CURRENT_TEST=")}

    expected_output = {
        "HOME=/home/user",
        "PATH=/usr/local/bin:/usr/bin:/bin",
        "SHELL=/bin/bash",
        "VALID_VAR=valid_value",
        "VAR_WITH_NUM_0=zero",
    }
    assert output_lines == expected_output
    assert stderr == ""


def test_specific_variables_printed_when_args_provided(run_main):
    """
    Tests if only specified environment variables are printed.
    """
    stdout, stderr = run_main(["HOME", "SHELL"])
    output_lines = set(stdout.strip().split('\n'))
    expected_lines = {"HOME=/home/user", "SHELL=/bin/bash"}
    assert output_lines == expected_lines
    assert stderr == ""


def test_nonexistent_variable_is_not_printed(run_main):
    """
    Tests that a non-existent variable is not printed and no error occurs.
    """
    stdout, stderr = run_main(["NON_EXISTENT_VAR"])
    assert stdout == ""
    assert stderr == ""


def test_variable_with_leading_number_is_filtered_out(run_main):
    """
    Tests that variables starting with a number are filtered out, even if specified.
    """
    stdout, stderr = run_main(["123_VAR"])
    assert stdout == ""
    assert stderr == ""


def test_variable_with_special_char_is_filtered_out(run_main):
    """
    Tests that variables starting with special characters like '$', '!', etc., are filtered out.
    """
    stdout, stderr = run_main(["@SPECIAL_VAR"])
    assert stdout == ""
    assert stderr == ""


def test_keyboard_interrupt_handling(run_main):
    """
    Tests if KeyboardInterrupt is handled gracefully.
    """
    with patch.object(os.environ, 'items', side_effect=KeyboardInterrupt):
        stdout, stderr = run_main([])

    assert stdout == ""
    assert "Operation interrupted by user." in stderr


def test_other_exception_handling(run_main):
    """
    Tests if a general exception is handled gracefully.
    """
    with patch.object(os.environ, 'items', side_effect=Exception("Test exception")):
        stdout, stderr = run_main([])

    assert stdout == ""
    assert "printenv: error: Test exception" in stderr
