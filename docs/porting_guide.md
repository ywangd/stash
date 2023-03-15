# Porting StaSh to another OS

This guide summarizes the process of porting StaSh to another platform.

## Important notes
- This document may be outdated. When this document describes the behavior of StaSh incorectly, the current behaviour of StaSh takes precedent (except when it is obviously a bug). In this case, please submit a fix to this document.
- Before you start porting, ensure your work is based on the latest `dev` status
- Read this document before starting your work, When I started adding an UI for desktop use, I had to switch the UI framework multiple times because I was not aware of all requirements.
- You will have to modify a few files already in place. When doing so, ensure the files **still run on both py2 and py3 without any non-standard dependencies**.
- Most of these methods may be called from threads. It is your responsibility to ensure that this works.
- There are no tests cases for the UI.


## Overview

The porting process can be divided into the following parts:

1. Porting the UI
2. Loading the UI correctly
3. Porting `libdist.py`
4. Updating the installer

## Getting started

You will need to find a way to accurately detect if StaSh runs on the target platform. This must be done using the standard library and must work with both py2 and py3.

For example, StaSh sets `ON_CI = "CI" in os.environ` to detect if we are running on GitHub Actions CI. In this case, a stub UI will be loaded.

## Porting the UI

1. Create a module for your UI in `system/shui/`. This guide will use `system/shui/myui.py`.
2. add a short (or long) docstring to `myui.py`
3. add the following imports: `from ..shscreens import ShChar`, `from ..shcommon import K_CC, K_CD, K_HUP, K_HDN, K_CU, K_TAB, K_HIST, K_CZ, K_KB`, `from .base import ShBaseUI, ShBaseTerminal, ShBaseSequentialRenderer`.
4. Subclass and implement `ShBaseUI`, `ShBaseTerminal`, `ShBaseSequentialRenderer`. See the following subsection.

The following subsection describes the required methods and attributes. **Please note the names of the subclasses.** For more examples, see `/system/shui/`.

### `class ShUI(ShBaseUI):`

This class represents the core of your UI.

- `__init__(self, *args, **kwargs)`:
  - pass both `*args` and `**kwargs` to `ShBaseUI.__init__`
  - do any initialization you have to do.
  - set `self.terminal` to an instance of your implementation of `ShBaseTerminal`.

- `show(self)`:
  - show the UI/window.

- `history_present(self, history)`:
  - history is the history to present (type `stash.system.shhistory.ShHistory`).
  - present a list of the history. When the user selects a line, call `self.history_selected(line, idx)` as described below.
- `history_selected(line, idx)`:
  - `line` is the selected line (type `str`)
  - `idx` is the index of the selected line
  - this method must be called when the user selected a history line when the history was presented(via `self.history_present`).
  - If you overwrite this method, be sure to call the base method.

- `on_exit(self)`:
   - This method must be called when the window will be closed.
   - If you overwrite this method, be sure to call the base method.
   
 - `*Action(self)`:
   - these are countless methods which should be called when the user performs the action described in the methods name. E.g. call `controlCAction` if the user presses `ctr` and `c`.

### `class ShTerminal(ShBaseTerminal):`
This class represents the text area in your UI.
**Please note that StaSh expects the text to be a single string.** This means that if StaSh references the index `200` in your text, it *may* be the 40th character in the 13th line. Linebreaks count towards the index.
Also note that StaSh uses `\n` as linebreaks, so you may need to convert those.

- `__init__(self, stash, parent)`:
   - `stash` is the `StaSh` instance. `parent` is your `ShUI`.
   - Initialize your text area here. Be sure to call `ShBaseTerminal.__init__`.
- `text`:
   - implement as a property.
   - a unicode string
   - get/set the text in your textarea.
- `text_length`:
   - the length of your text. By default, use `len(self.text)`
- `selected_range`:
   - implement as a property
   - `tuple` of `(int, int)`, representing startindex and endindex of the selected text.
   - remember that StaSh sees the terminal text as a single string, so you may have to convert the index of your UI.
   - when modified, set `self.cursor_synced = False`
- `get_wh(self)`:
    - return the number of columns and rows in the terminal as a tuple of ( `int`, `int`)

- `scroll to end(self)`:
   - scroll towards the end.
- `set_focus(self)`:
   - If possible, set the input focus of the OS to the terminal.
- `lose_focus(self)`:
   - If possible, lose the input focus of the OS.
- `replace_in_range(self, rng, text)`:
   - rng is the range to replace, **as (start, length)**. `text` is the new text (depending on your renderer, either `str` or a sequence of `ShChar`s). 
   - replace the text in the given range.
   - the most important method for the UI (except when using a different renderer implementation).
   - if the text consits of `ShChar`s, you may want to handle colors and other styles. See `system.shscreens.ShChar` for more details.
- `tv_delegate`:
    - type `system.shui.base.ShTerminalDelegate`
    - created and set in `ShBaseTerminal.__init__()` / you do not have to create it yourself
    - **when interacting with it, try to call the respective `stash.user_action_proxy.tv_responder.*` methods instead.**
    - has a couple of callbacks which needs to be called at the correct time:
        - call `textview_did_begin_editing(tv)` when the user starts editing/the textarea received input focus. `tv` is the terminal.
        - call `textview_did_end_editing(tv)` when the user stops editing/the textarea loses input focus. `tv` is the terminal
        - call `textview_should_change(tv, rng, replacement)` when the user modifies the content of the textarea. Only perform the modification if  this results in a nonzero value. `tv` is the terminal, `rng` is tuple of `(startindex, endindex)`. `replacement` is the new content.
        - call `textview_did_change(tv)` if the content of the textarea was changed. `tv` is the terminal.
        - call `textview_did_change_selection(self, tv)` when `self.selected_range` was changed.
- `debug`:
    - type `bool`
    - set automatically by `ShBaseTerminal.__init__`
    - if True, print additional debug information


### `class ShSequentialRenderer(ShBaseSequentialRenderer):`

This class is responsible for rendering the text onto your terminal.
`You should take a look at the implementation in `system/shui/tkui.py`.`

- `__init__(self, *args, **kwargs)`:
    - pass `*args` and `**kwargs` to `ShBaseSequentialRenderer.__init__()`
    - if your UI disallows access from other threads, you may need to setup some loop running in the mainloop here.

- `render(self, no_wait=False)`:
    - render the text on to the terminal
    - if `no_wait` is True, do not delay rendering.
    - **chances are that you do not have to implement this method yourself. Instead, copy&paste the content in the next subsection.
- `FG_COLORS` and `BG_COLORS`:
    - `dicts` of colorname (`str`) to a value. Type of value is only relevant to your implementation of `ShBaseTerminal.replace_in_range`.
    - these are the foreground and background colors.
    - should at least contain `"default": None`.
    - `default` will be modified according to the settings.

#### Code for `render()`:
This code is a modified version copy&pasted from `tkui.py`, which in turn got it from the original UI.
```python
    def render(self, no_wait=False):
        # Lock screen to get atomic information
        with self.screen.acquire_lock():
            intact_left_bound, intact_right_bound = self.screen.get_bounds()
            screen_buffer_length = self.screen.text_length
            cursor_xs, cursor_xe = self.screen.cursor_x
            renderable_chars = self.screen.renderable_chars
            self.screen.clean()
        
        # First remove any leading texts that are rotated out
        if intact_left_bound > 0:
            self.terminal.replace_in_range((0, intact_left_bound), '')

        tv_text_length = self.terminal.text_length  # tv_text_length = tvo_texts.length()

        # Second (re)render any modified trailing texts
        # When there are contents beyond the right bound, either on screen
        # or on terminal, the contents need to be re-rendered.
        if intact_right_bound < max(tv_text_length, screen_buffer_length):
            if len(renderable_chars) > 0:
                self.terminal.replace_in_range(
                    (intact_right_bound,
                     tv_text_length - intact_right_bound),
                    # "".join([c.data for c in renderable_chars]),
                    renderable_chars,
                )
            else:  # empty string, pure deletion
                self.terminal.replace_in_range(
                    (intact_right_bound,
                     tv_text_length - intact_right_bound),
                    '',
                )

        # Set the cursor position. This makes terminal and main screen cursors in sync
        self.terminal.selected_range = (cursor_xs, cursor_xe)

        # Ensure cursor line is visible by scroll to the end of the text
        self.terminal.scroll_to_end()
```

## Loading the UI correctly

The UI must be correctly loaded in order to work.
Please ensure that you have a way to identify your target platform.

1. edit `stash/system/shui/__init__.py`
2. edit the `get_platform()` function to return a identifier for your platform/UI.
3. edit the `get_ui_implementation()` function. see the `if ...: ... else: ...` construct there? Simply add `    elif platform == "<my-platform-identifier>":\n        from .myui import ShUI, ShTerminal, ShSequentialRenderer\n    return (ShUI, ShSequentialRenderer)`.
4. save


## Porting `libdist`

StaSh uses a file called `libdist.py` for os-specific interactions and values.

1. edit `stash/lib/libdist.py`
2. add your check at the top of the file (near `ON_CI = ...`)
3. See the large top-level `if ... elif ... else` consturct there? add a `elif <mycondition>:` there.
4. implement the functions and define the values used in the other cases. In the next subsection is an overview of these definitions.
5. save


### Overview of `libdist`

- `clipboard_get()` and `clipboard_set(s)`: get or set the clipbopard. works with unicode.
- `SITE_PACKAGES_FOLDER` is the path to the directoy in which `pip` will install modules into.
- `SITE_PACKAGES_FOLDER_6` is like `SITE_PACKAGES_FOLDER`, but should point to a directory shared by py2 and py3. If unavailable, use `None`.
- `BUNDLED_MODULES` is a list of `str`. It contains the preinstalled 3rd party modules. `pip` will skip these modules.
- `open_in(path)` should open the given file in another application. If possible, let the user decide.
- `quicklook(path)` should show a quicklook at the file. May be the same as `open_in`.

## Updating the installer

The StaSh installation is handled by `getstash.py` in the StaSh root directory. Add your check and install as neccessary.
At the top of the `main()` function are a couple of definitions. Please do not modify these definitions and try to handle them if possible.
**Please note that `getstash.py` is also used by `selfupdate`.** Thus, ensure that `getstash.py` stays backwards compatible with older versions.
