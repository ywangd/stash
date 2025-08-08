"""
This is a stub file for the `editor` module, providing type hints for its
functions and their parameters, to be used for static analysis and autocompletion.
"""

from typing import Optional, Tuple, Literal

# We'll use a minimal stub for the ui.View type from the ui module.
class View: ...

def get_path() -> Optional[str]:
    """Returns the absolute file path of the script that is currently open in the editor.

    Returns:
        Optional[str]: The absolute file path, or None if no script is open.
    """
    ...

def get_text() -> str:
    """Returns the entire text of the script that is currently being edited.

    Returns:
        str: The full text content of the editor.
    """
    ...

def get_selection() -> Optional[Tuple[int, int]]:
    """Returns the selected range as a tuple of the form (start, end).

    The `start` and `end` values are character indices.

    Returns:
        Optional[Tuple[int, int]]: The start and end indices of the selection,
            or None if no file is currently open.
    """
    ...

def get_line_selection() -> Optional[Tuple[int, int]]:
    """Returns the range of all lines that are part of the current selection.

    Returns:
        Optional[Tuple[int, int]]: The start and end indices of the line selection,
            or None if no file is currently open.
    """
    ...

def set_selection(start: int, end: Optional[int] = None, scroll: bool = False) -> None:
    """Sets the selected range in the editor.

    Args:
        start (int): The starting character index of the selection.
        end (Optional[int], optional): The ending character index of the selection.
            If None, the caret is positioned at `start` with no text selected.
        scroll (bool, optional): If True, scrolls the view to make the selection
            visible. Defaults to False.
    """
    ...

def replace_text(start: int, end: int, replacement: str) -> None:
    """Replaces the text in the given range with a new string.

    To insert/append text, a zero-length range can be used. All changes can be
    undone by the user (using the regular undo key).

    Args:
        start (int): The starting character index of the range to replace.
        end (int): The ending character index of the range to replace.
        replacement (str): The new text to insert.
    """
    ...

def make_new_file(name: Optional[str] = None, content: Optional[str] = None) -> None:
    """Creates a new file and opens it in the editor.

    If a file with the given name already exists, a numeric suffix is
    automatically appended.

    Args:
        name (Optional[str], optional): The desired name for the new file.
            Defaults to None.
        content (Optional[str], optional): The initial content of the new file.
            If omitted, an empty file is created. Defaults to None.
    """
    ...

def open_file(name: str, new_tab: bool = False) -> None:
    """Opens the file with the given name in the editor.

    Args:
        name (str): The path to the file. It can be relative to the script
            library’s root directory or an absolute path. The .py extension
            can be omitted.
        new_tab (bool, optional): If True, the file is opened in a new tab.
            Defaults to False.
    """
    ...

def apply_ui_theme(ui_view: View, theme_name: Optional[str] = None) -> None:
    """Styles a ui.View (and its descendents) with the given UI theme.

    Args:
        ui_view (ui.View): The view to be styled.
        theme_name (Optional[str], optional): The name of the theme. If None,
            the currently selected theme is used. Defaults to None.
    """
    ...

def present_themed(ui_view: View, theme_name: Optional[str] = None, **kwargs) -> None:
    """Styles a ui.View and presents it.

    This function combines `apply_ui_theme()` and `ui.View.present()`.
    Keyword arguments are passed on to `ui.View.present()`.

    Args:
        ui_view (ui.View): The view to be styled and presented.
        theme_name (Optional[str], optional): The name of the theme. If None,
            the currently selected theme is used. Defaults to None.
    """
    ...

_AnnotationStyle = Literal["success", "warning", "error"]

def annotate_line(
    lineno: int,
    text: str = "",
    style: _AnnotationStyle = "warning",
    expanded: bool = True,
    filename: Optional[str] = None,
    scroll: bool = False,
) -> None:
    """Annotates a line of code in the editor with a label.

    Args:
        lineno (int): The 1-based line number to annotate.
        text (str, optional): The text of the annotation. Defaults to ''.
        style (Literal['success', 'warning', 'error'], optional): The style of
            the annotation. Defaults to 'warning'.
        expanded (bool, optional): If False, only an icon is shown; tapping
            shows the text. Defaults to True.
        filename (Optional[str], optional): The path to the file to annotate.
            If None, the file currently open in the editor is used.
            Defaults to None.
        scroll (bool, optional): If True, scrolls to the annotated line.
            Defaults to False.
    """
    ...

def clear_annotations(filename: Optional[str] = None) -> None:
    """Removes all annotations that were added via `annotate_line()`.

    Args:
        filename (Optional[str], optional): The path to the file from which to
            clear annotations. If None, the file currently open is used.
            Defaults to None.
    """
    ...
