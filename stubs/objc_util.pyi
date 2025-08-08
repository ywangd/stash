"""Utilities for bridging Objective-C APIs.

This module provides a "bridge" for using Objective-C APIs from Python.
Based on ctypes and the Objective-C runtime library, objc_util allows
you to "wrap" existing Objective-C classes in a way that automatically
converts Python method calls to corresponding Objective-C messages.
"""

from typing import (
    Any,
    Callable,
    List,
    Optional,
    TypeVar,
)

# A type variable for the decorator to preserve function signatures.
F = TypeVar("F", bound=Callable)

class ObjCClass:
    """Wrapper for an Objective-C class.

    Acts as a proxy for calling Objective-C class methods. Method calls are
    converted to Objective-C messages on-the-fly. This is done by replacing
    underscores in the method name with colons in the selector name, and
    using the selector and arguments for a call to the low-level objc_msgSend()
    function.

    Example:
        Calling `NSDictionary.dictionaryWithObject_forKey_(obj, key)` in Python is
        translated to `[NSDictionary dictionaryWithObject:obj forKey:key]`
        in Objective-C.

    Args:
        name: The name of the Objective-C class as a string.
    """

    def __init__(self, name: str) -> None:
        pass

class ObjCInstance:
    """Wrapper for a pointer to an Objective-C object.

    Acts as a proxy for sending messages to the object. Method calls are converted
    to Objective-C messages on-the-fly.

    Example:
        Calling `obj.setFoo_withBar_(foo, bar)` in Python is translated to
        `[obj setFoo:foo withBar:bar]` in Objective-C.

    Args:
        ptr: A pointer to the Objective-C object.
    """

    def __init__(self, ptr: Any) -> None:
        pass

class ObjCBlock:
    """Wrapper for Objective-C blocks (closures).

    Note:
        Block support is experimental.

    Args:
        func: The Python function to wrap as a block.
        restype: The return type of the block (e.g., `NSInteger`).
        argtypes: A list of argument types for the block.
    """

    def __init__(
        self, func: Callable, restype: Any = None, argtypes: Optional[List[Any]] = None
    ) -> None:
        pass

def autoreleasepool() -> Any:
    """A context manager for NSAutoreleasePool.

    This acts as a wrapper for `NSAutoreleasePool` (similar to
    `@autoreleasepool {...}` in Objective-C).

    Usage:
        with objc_util.autoreleasepool():
            # do stuff...

    Returns:
        A context manager for an autorelease pool.
    """
    ...

def create_objc_class(
    name: str,
    superclass: ObjCClass = ...,
    methods: Optional[List[Callable]] = None,
    classmethods: Optional[List[Callable]] = None,
    protocols: Optional[List[str]] = None,
    debug: bool = True,
) -> ObjCClass:
    """Create and return a new ObjCClass.

    The selector name is derived from the name of the function. The return and
    argument types are inferred automatically from the superclass or protocols
    if possible.

    Args:
        name: The name of the class to create.
        superclass: The ObjCClass object from which the new class inherits.
        methods: A list of functions for instance methods.
        classmethods: A list of functions for class methods.
        protocols: A list of protocol names (strings) for type hinting.
        debug: If `True`, a new name will be chosen automatically if a class
            with `name` already exists.

    Returns:
        A new ObjCClass object.
    """
    ...

def load_framework(name: str) -> None:
    """Load the system framework with the given name.

    Args:
        name: The name of the framework (e.g., 'SceneKit').
    """
    ...

def ns(obj: Any) -> Any:
    """Convert a Python object to its Objective-C equivalent.

    Converts `str` to `NSString`, `list` to `NSMutableArray`, `dict` to
    `NSMutableDictionary`, etc. Nested structures are supported.

    Args:
        obj: The Python object to convert.

    Returns:
        The Objective-C equivalent of the input object, wrapped in an
        ObjCInstance if applicable.
    """
    ...

def nsurl(url_or_path: str) -> ObjCInstance:
    """Convert a Python string to an NSURL object.

    Args:
        url_or_path: A string representing a URL or a file path.

    Returns:
        An `NSURL` object wrapped in an `ObjCInstance`.
    """
    ...

def nsdata_to_bytes(data: ObjCInstance) -> bytes:
    """Convert an NSData object to a Python byte string.

    Args:
        data: An `NSData` object wrapped in an `ObjCInstance`.

    Returns:
        A Python byte string.
    """
    ...

def uiimage_to_png(img: ObjCInstance) -> bytes:
    """Convert a UIImage object to a Python byte string with PNG data.

    Args:
        img: A `UIImage` object wrapped in an `ObjCInstance`.

    Returns:
        A Python byte string containing PNG data.
    """
    ...

def on_main_thread(func: F) -> F:
    """Decorator to call a function on the UIKit main thread.

    This is typically used to decorate another function, but can also be used
    ad-hoc for dispatching a function call to the main thread.

    Args:
        func: The function to be executed on the main thread.

    Returns:
        The decorated function.
    """
    ...

def sel(name: str) -> Any:
    """Convert a Python string to an Objective-C selector.

    Args:
        name: The name of the selector as a string.

    Returns:
        An Objective-C selector object.
    """
    ...

# Convenience class wrappers for common Objective-C types
# These are included as module-level objects for convenience.
class CGPoint: ...
class CGSize: ...
class CGVector: ...
class CGRect: ...
class CGAffineTransform: ...
class UIEdgeInsets: ...
class NSRange: ...
class NSDictionary(ObjCClass): ...
class NSMutableDictionary(ObjCClass): ...
class NSArray(ObjCClass): ...
class NSMutableArray(ObjCClass): ...
class NSSet(ObjCClass): ...
class NSMutableSet(ObjCClass): ...
class NSString(ObjCClass): ...
class NSMutableString(ObjCClass): ...
class NSData(ObjCClass): ...
class NSMutableData(ObjCClass): ...
class NSNumber(ObjCClass): ...
class NSURL(ObjCClass): ...
class NSEnumerator(ObjCClass): ...
