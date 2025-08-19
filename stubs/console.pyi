"""
This is a stub file for the `console` module, providing type hints for its
functions and their parameters, to be used for static analysis and autocompletion.
"""

from typing import Optional, Union, Tuple, Sequence, Literal

# These are simple utility functions.
def clear() -> None:
    """Clears the console output."""
    ...

def set_font(name: Optional[str] = None, size: Optional[int] = None) -> None:
    """Sets the font and font size for the following output.

    Args:
        name (str, optional): The font name (e.g. "Menlo"). If None, reset to default.
        size (int, optional): The font size. If None, reset to default.
    """
    ...

def set_color(r: float, g: float, b: float) -> None:
    """Sets the RGB colour for the following output.

    The components are floats between 0.0 and 1.0.

    Args:
        r (float): The red component.
        g (float): The green component.
        b (float): The blue component.
    """
    ...

def secure_input(prompt: Optional[str] = None) -> str:
    """Gets user input with hidden characters.

    This function is similar to the built-in raw_input function, but the user’s
    input is hidden, so that it’s suitable to request passwords and other
    sensitive information.

    Args:
        prompt (str, optional): A prompt to display to the user.

    Returns:
        str: The string entered by the user.
    """
    ...

def show_image(image_path: Union[str]) -> None:
    """Shows an image in the console output area.

    Args:
        image_path (str or Path): The path to the image file.
    """
    ...

def alert(
    title: str,
    message: str = "",
    button1: str = "OK",
    button2: Optional[str] = None,
    button3: Optional[str] = None,
    hide_cancel_button: bool = False,
) -> int:
    """Shows an alert dialog with up to three custom buttons.

    The selected button is returned as an integer (button1 => 1, etc.).
    Unless `hide_cancel_button` is True, all alert dialogs contain a ‘Cancel’
    button that sends a KeyboardInterrupt.

    Args:
        title (str): The title of the alert.
        message (str, optional): The message to display. Defaults to "".
        button1 (str, optional): The title of the first button. Defaults to "OK".
        button2 (str, optional): The title of the second button.
        button3 (str, optional): The title of the third button.
        hide_cancel_button (bool, optional): If True, hides the cancel button.
            Defaults to False.

    Returns:
        int: The integer corresponding to the selected button (1, 2, or 3).
    """
    ...

def input_alert(
    title: str,
    message: str = "",
    input: str = "",
    ok_button_title: str = "OK",
    hide_cancel_button: bool = False,
) -> str:
    """Shows a dialog with a single text field.

    The text field can be pre-filled with the `input` parameter. The text
    that was entered by the user is returned. The ‘Cancel’ button sends a
    KeyboardInterrupt.

    Args:
        title (str): The title of the alert.
        message (str, optional): The message to display. Defaults to "".
        input (str, optional): Text to pre-fill the input field with.
            Defaults to "".
        ok_button_title (str, optional): The title of the OK button.
            Defaults to "OK".
        hide_cancel_button (bool, optional): If True, hides the cancel button.
            Defaults to False.

    Returns:
        str: The text entered by the user.
    """
    ...

def password_alert(
    title: str,
    message: str = "",
    password: str = "",
    ok_button_title: str = "OK",
    hide_cancel_button: bool = False,
) -> str:
    """Shows a dialog with a password entry text field.

    The password field can be pre-filled with the `password` parameter.
    The password that was entered by the user is returned. The ‘Cancel’ button
    sends a KeyboardInterrupt.

    Args:
        title (str): The title of the alert.
        message (str, optional): The message to display. Defaults to "".
        password (str, optional): Text to pre-fill the password field with.
            Defaults to "".
        ok_button_title (str, optional): The title of the OK button.
            Defaults to "OK".
        hide_cancel_button (bool, optional): If True, hides the cancel button.
            Defaults to False.

    Returns:
        str: The password entered by the user.
    """
    ...

def login_alert(
    title: str,
    message: str = "",
    login: str = "",
    password: str = "",
    ok_button_title: str = "OK",
) -> Tuple[str, str]:
    """Shows a dialog with two text fields, one for login and one for a password.

    The text fields can be pre-filled with the `login` and `password` parameters.
    Returns a tuple of the entered text as `(login, password)`. The ‘Cancel’
    button sends a KeyboardInterrupt.

    Args:
        title (str): The title of the alert.
        message (str, optional): The message to display. Defaults to "".
        login (str, optional): Text to pre-fill the login field with.
            Defaults to "".
        password (str, optional): Text to pre-fill the password field with.
            Defaults to "".
        ok_button_title (str, optional): The title of the OK button.
            Defaults to "OK".

    Returns:
        Tuple[str, str]: A tuple containing the entered login and password.
    """
    ...

def show_activity() -> None:
    """Shows the animated “network activity indicator” in the status bar."""
    ...

def hide_activity() -> None:
    """Hides the animated “network activity indicator” in the status bar."""
    ...

_HudIcon = Literal["success", "error"]

def hud_alert(message: str, icon: _HudIcon = "success", duration: float = 1.8) -> None:
    """Shows a HUD-style alert with the given message.

    The function blocks until the alert is dismissed.

    Args:
        message (str): The message to display.
        icon (str, optional): The icon to show. It Can be 'success' (a checkmark
            symbol) or 'error' (a cross symbol). Defaults to 'success'.
        duration (float, optional): How long the alert is shown. It Can be
            between 0.25 and 5.0 seconds. Defaults to 1.8 seconds.
    """
    ...

def write_link(title: str, link_url: str) -> None:
    """Prints a tappable link to the console.

    Args:
        title (str): The title of the link to display.
        link_url (str): The URL link should open.
    """
    ...

def hide_output() -> None:
    """Hides the console output area with a sliding animation."""
    ...

def quicklook(file_path: Union[str, Sequence[str]]) -> None:
    """Shows a full-screen preview of local files.

    The function returns when the preview is dismissed.

    Args:
        file_path (str or Path or Sequence): The path to a single file, or
            a sequence of paths to preview multiple files.
    """
    ...

def open_in(file_path: str) -> Optional[str]:
    """Shows the iOS “Open in...” menu for the specified file.

    Args:
        file_path (str or Path): The path to the file.

    Returns:
        Optional[str]: The bundle identifier of the selected app, or None
            if the menu was cancelled or no app can open the file.
    """
    ...

def set_idle_timer_disabled(flag: bool) -> None:
    """Disables or enables the idle timer.

    Args:
        flag (bool): If True, the idle timer is disabled (a device won't go to
            sleep). If False, the idle timer is re-enabled.
    """
    ...

def is_in_background() -> bool:
    """Returns whether the app is currently running in the background.

    Returns:
        bool: True if the app is in the background, False otherwise.
    """
    ...
