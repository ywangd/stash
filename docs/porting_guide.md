# Porting StaSh to another OS

This guide summarizes the process of porting StaSh to another platform.

## Important notes
- This document may be outdated. When this document describes the behavior of StaSh incorectly, the current behaviour of StaSh takes precedent (except when its obiously a bug). In this case, please submit a fix to this document.
- Before you start porting, ensure your work is based on the latest dev status
- Read this document before starting your work, When I started adding an UI for desktop use, I had to switch the UI framework multiple times because I was not aware of all requirements.
- You will have to modify a few files already in place. When doing so, ensure the files **still run on both py2 and py3 without any non-standard dependencies**.
- most of these methods may be called from threads. It is your responsibility to ensure that this works.
- There are no tests cases for the UI.


## Overview

The porting process can be divided into the following parts:

1. porting the UI
2. loading the UI correctly
3. porting `libdist`
4. updating the installer

## Getting started

You will need to find a way to accurately detect if StaSh runs on the target platform. This must be done using the standard library and must work with both py2 and py3.

## Porting the UI

1. Create a module for your UI in `system/shui/`. This guide will use `system/shui/myui.py`.
2. add a short (or long) docstring to `myui.py`
3. add the following imports: `from ..shscreens import ShChar`, `from ..shcommon import K_CC, K_CD, K_HUP, K_HDN, K_CU, K_TAB, K_HIST, K_CZ, K_KB`, `from .base import ShBaseUI, ShBaseTerminal, ShBaseSequentialRenderer`.
4. subclass and implement `ShBaseUI`, `ShBaseTerminal`, `ShBaseSequentialRenderer`. See the following subsection.

The following subsection describes the required methods. **Please note the names of the subclasses.** For more examples, see `/system/shui/`.

### `class ShUI(ShBaseUI):`

This class represents the core of your UI.

- `__init__(self, *args, **kwargs)`:
  - pass both `*args` and `**kwargs` to `ShBaseUI.__init__`
  - do any initialization you have to do.
  - set `self.terminal` to your implementation of `ShBaseTerminal`.
 
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

#### code for `render()`:
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

more coming soon
