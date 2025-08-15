"""
This is a stub file for the `clipboard` module, providing type hints for its
functions and their parameters, to be used for static analysis and autocompletion.
"""

from typing import Optional, Literal

# Assuming 'PIL' is from the Pillow library, which is not part of the standard library
# and might not be available in all Pythonista environments.
# We'll use `Any` as a fallback or assume a type alias exists.
try:
    from PIL.Image import Image
except ImportError:
    from typing import Any as Image

def get() -> str:
    """Returns the clipboard’s content as a Unicode string.

    Returns:
        str: The content of the clipboard.
    """
    ...

def set(string: str) -> None:
    """Sets the clipboard’s content to a new string.

    Args:
        string (str): The new content for the clipboard.
    """
    ...

def get_image(idx: int = 0) -> Optional[Image]:
    """Returns an image from the clipboard.

    If there are multiple images in the clipboard, the `idx` parameter can be
    used to get an image at a given index. If the index is >= the number of
    images in the clipboard, `None` is returned.

    Args:
        idx (int, optional): The index of the image to retrieve. Defaults to 0.

    Returns:
        Optional[Image]: The image from the clipboard, or None if no image
            was found at the given index.
    """
    ...

_ImageFormat = Literal["png", "jpeg"]

def set_image(
    image: Image, format: _ImageFormat = "png", jpeg_quality: float = 0.75
) -> None:
    """Stores a given PIL Image in the clipboard.

    Args:
        image (PIL.Image.Image): The image to store in the clipboard.
        format (str, optional): The format to store the image in. Can be
            'png' or 'jpeg'. Defaults to 'png'.
        jpeg_quality (float, optional): The quality for JPEG format. Should be
            a float between 0.0 and 1.0. This is ignored if `format` is 'png'.
            Defaults to 0.75.
    """
    ...
