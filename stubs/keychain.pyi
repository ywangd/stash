"""Secure Password Storage.

This module provides simple access to secure password storage.

Note:
    The keychain is not shared between apps, so you cannot use this to
    access passwords stored in Safari's keychain, for example.
"""

from typing import Optional

def get_password(service: str, account: str) -> Optional[str]:
    """Get a password from the keychain.

    Args:
        service: The name of the service associated with the password.
        account: The name of the user account associated with the password.

    Returns:
        The password as a string, or `None` if no password is found
        for the given service and account.
    """
    ...

def set_password(service: str, account: str, password: str) -> None:
    """Save a password to the keychain.

    This saves a password for the given service and account. If a password
    already exists for this service/account pair, it will be overwritten.

    Args:
        service: The name of the service to associate with the password.
        account: The name of the user account.
        password: The password to be stored.
    """
    ...

def delete_password(service: str, account: str) -> None:
    """Delete a password from the keychain.

    This deletes the password for the given service and account.

    Args:
        service: The name of the service.
        account: The name of the user account.
    """
    ...

def reset_keychain() -> None:
    """Delete all data from the keychain.

    This is a destructive operation that removes all passwords
    stored by the current application.
    """
    ...
