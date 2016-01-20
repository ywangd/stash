# coding: utf-8
import logging
from time import time

import threading
from collections import deque, namedtuple
from contextlib import contextmanager

try:
    from objc_util import *
except ImportError:
    from dummyobjc_util import *

from .shcommon import IN_PYTHONISTA, ON_IOS_8
from .shcommon import Graphics as graphics, Control as ctrl, Escape as esc

NSMutableAttributedString = ObjCClass('NSMutableAttributedString')
UIFont = ObjCClass('UIFont')

BlackColor = UIColor.blackColor()
RedColor = UIColor.redColor()
GreenColor = UIColor.greenColor()
BrownColor = UIColor.brownColor()
# BlueColor = UIColor.blueColor()
BlueColor = UIColor.colorWithRed_green_blue_alpha_(0.3, 0.3, 1.0, 1.0)
MagentaColor = UIColor.magentaColor()
CyanColor = UIColor.cyanColor()
WhiteColor = UIColor.whiteColor()
GrayColor = UIColor.colorWithRed_green_blue_alpha_(0.5, 0.5, 0.5, 1.0)
YellowColor = UIColor.yellowColor()
SmokeColor = UIColor.colorWithRed_green_blue_alpha_(0.8, 0.8, 0.8, 1.0)


class ShScreenNotLocked(Exception):
    pass


#: A container for a single character, field names are *hopefully*
#: self-explanatory.
_Char = namedtuple("_Char", [
    "data",
    "fg",
    "bg",
    "bold",
    "italics",
    "underscore",
    "strikethrough",
    "reverse",
])

class ShChar(_Char):
    
    """
    Class of attributed character.
    :param str data: The actual character
    :param str fg: The foreground color
    :param str bg: The background color
    :param bool bold: Bold font
    :param bool italics: Italics font
    :param bool underscore: Underline the character
    :param bool reverse: NOT Implemented
    :param bool strikethrough: Strike through the character
    """
    __slots__ = ()

    # noinspection PyInitNewSignature
    def __new__(cls, data, fg="default", bg="default", bold=False,
                italics=False, underscore=False, reverse=False,
                strikethrough=False):
        return _Char.__new__(cls, data, fg, bg, bold, italics, underscore,
                             strikethrough, reverse)


DEFAULT_CHAR = ShChar(data=' ', fg='default', bg='default')

# noinspection PyAttributeOutsideInit
class ShSequentialScreen(object):

    """
    The sequential type in-memory screen. Running scripts can only
    add characters at the end of the screen buffer, no backspace or
    cursor movement is possible. Hence it is sequential.
    :param int nlines_max: The maximum number of lines to be stored.
    """

    def __init__(self, stash, nlines_max=100, debug=False):

        self.stash = stash
        self.nlines_max = nlines_max
        self.debug = debug
        self.logger = logging.getLogger('StaSh.Screen')

        self.buffer = deque()  # buffer to hold chars
        self.lock = threading.Lock()

        self.attrs = ShChar(' ')

        self.reset()

    def reset(self, *args):  # *args is a necessary placeholder
        """
        Clear the screen and reset its state.
        *args is needed because dispatch from stream always call handlers
        with at least one parameter (even it is a dummy 0).
        """
        # empty the buffer
        self.buffer.clear()

        # The cursor position
        self.cursor_x = 0

        # This is the location where modifiable chars start. It is immediately
        # after where latest program write ends.
        self.x_drawend = 0
        # The left and right bounds of rendered chars
        # All chars before this location must be removed from terminal text.
        # Note this value is relative to start of Terminal text.
        self.intact_left_bound = 0
        # All chars after this location must be re-rendered. Note this value is
        # relative to start of the Screen's buffer.
        self.intact_right_bound = 0

        self.nlines = 0

    @property
    def text(self):
        """
        :rtype: str
        """
        return ''.join(char.data for char in self.buffer)

    @property
    def renderable_chars(self):
        """
        Note this return a list of ShChar not string.
        Trailing characters that need to be re-rendered.
        :rtype: [ShChar]
        """
        _, rbound = self.get_bounds()
        return [self.buffer[x] for x in range(rbound, len(self.buffer))]

    @property
    def x_modifiable(self):
        """
        The location where characters can be modified by users. The value
        is relative to beginning of the screen buffer.
        :rtype: int
        """
        # The position is either the x_drawend or last LF location plus one,
        # whichever is larger.
        for idx in reversed(range(self.x_drawend, len(self.buffer))):
            if self.buffer[idx].data == '\n':
                return idx + 1
        else:
            return self.x_drawend

    @property
    def modifiable_chars(self):
        """
        :rtype: str
        """
        return ''.join(self.buffer[idx].data
                       for idx in range(self.x_modifiable, len(self.buffer)))

    @modifiable_chars.setter
    def modifiable_chars(self, s):
        """
        Set the modifiable_chars to the given string.
        :param str s: A new value for modifiable_chars.
        """
        self.replace_in_range((self.x_modifiable, len(self.buffer)), s)

    @contextmanager
    def acquire_lock(self):
        """
        Lock the screen for modification so that it will not be corrupted.
        """
        try:
            ret = self.lock.acquire()
            # if self.debug:
            #     self.logger.debug('Lock Acquired')
            yield ret
        finally:
            self.lock.release()
            # if self.debug:
            #     self.logger.debug('Lock Released')
            
    def get_bounds(self):
        """
        The bounds could become negative if entire screen is flushed out before
        any rendering. In this case, the bounds need to be adjusted accordingly.
        :rtype (int, int):
        """
        rbound = self.intact_right_bound if self.intact_right_bound >= 0 else 0
        lbound = self.intact_left_bound if rbound > 0 else 0
        return lbound, rbound

    def clean(self):
        """
        Mark everything is rendered.
        """
        self.intact_left_bound = 0
        self.intact_right_bound = len(self.buffer)

    # noinspection PyProtectedMember
    def draw(self, c):
        """
        Add given char to the right end of the buffer and update the last draw
        location. This method should ONLY be called by ShStream.
        :param str c: A new character to draw
        """
        if len(self.buffer) < self.intact_right_bound:
            self.intact_right_bound = len(self.buffer)

        self.buffer.append(self.attrs._replace(data=c))
        self.cursor_x = self.x_drawend = len(self.buffer)

        if c == '\n':
            self.nlines += 1
            self._ensure_nlines_max()

    # noinspection PyProtectedMember
    def replace_in_range(self, rng, s, relative_to_x_modifiable=False, set_drawend=False):
        """
        Replace the buffer content in the given range. This method should
        ONLY be called from the UI delegation side, i.e. NOT running
        scripts.
        :param (int, int) rng: Range of buffer to be replaced
        :param str s: String to be inserted (to be converted to Char with default properties).
        :param bool relative_to_x_modifiable: If True, the range is relative to the x_modifiable
        :param bool set_drawend: If True, the x_drawend will be set to the end of this replacement.
        :return:
        """
        if rng is None:
            rng = (len(self.buffer), len(self.buffer))

        elif relative_to_x_modifiable:  # Convert to absolute location if necessary
            rng = rng[0] + self.x_modifiable, rng[1] + self.x_modifiable

        # Update the right bound if necessary
        if rng[0] < self.intact_right_bound:
            self.intact_right_bound = rng[0]

        rotate_n = max(len(self.buffer) - rng[1], 0)
        try:
            self.buffer.rotate(rotate_n)  # rotate buffer first so deletion is possible
            if rng[0] != rng[1]:  # delete chars if necessary
                self._pop_chars(rng[1] - rng[0])
            # The newly inserted chars are always of default properties
            self.buffer.extend(DEFAULT_CHAR._replace(data=c) for c in s)

        finally:
            self.buffer.rotate(-rotate_n)

        # Update cursor to the end of this replacement
        self.cursor_x = rng[0] + len(s)

        # Normally the draw end is not set
        if set_drawend:
            self.x_drawend = self.cursor_x

        nlf = s.count('\n')
        if nlf > 0:
            self.nlines += nlf
            self._ensure_nlines_max()

    def ensure_cursor_in_modifiable_range(self):
        if self.cursor_x > len(self.buffer):
            self.cursor_x = len(self.buffer)
        elif self.cursor_x < self.x_modifiable:
            self.cursor_x = self.x_modifiable

    def _pop_chars(self, n=1):
        """
        Remove number of given characters form the right END of the buffer
        :param n:
        :return:
        """
        for _ in range(n):
            self.buffer.pop()
            if len(self.buffer) < self.intact_right_bound:
                self.intact_right_bound = len(self.buffer)

    def _ensure_nlines_max(self):
        """
        Keep number of lines under control
        """
        char_count = line_count = 0
        for _ in range(self.nlines_max, self.nlines):
            # Remove the top line
            for idx in range(len(self.buffer)):
                char_count += 1
                if self.buffer.popleft().data == '\n':
                    line_count += 1
                    break

        self.intact_left_bound += char_count
        self.intact_right_bound -= char_count
        self.cursor_x -= char_count
        self.x_drawend -= char_count
        self.nlines -= line_count

    # noinspection PyProtectedMember
    def select_graphic_rendition(self, *attrs):
        """
        Act on text style ASCII escapes
        :param [ShChar] attrs: List of characters and their attributes
        """
        replace = {}

        for attr in attrs or [0]:
            if attr in graphics.FG:
                replace["fg"] = graphics.FG[attr]
            elif attr in graphics.BG:
                replace["bg"] = graphics.BG[attr]
            elif attr in graphics.TEXT:
                attr = graphics.TEXT[attr]
                replace[attr[1:]] = attr.startswith("+")
            elif not attr:
                replace = DEFAULT_CHAR._asdict()

        self.attrs = self.attrs._replace(**replace)


def sh_delay(func, nseconds):
    t = threading.Timer(nseconds, func)
    t.start()
    return t


class ShSequentialRenderer(object):

    """
    A specific renderer for `ShSequentialScreen`. It does its job by
    building texts from the in-memory screen and insert them to the
    UI terminal.
    :param ShSequentialScreen screen: In memory screen
    :param system.shterminal.ShTerminal terminal: The real UI terminal
    """
    FG_COLORS = {
        'black': BlackColor,
        'red': RedColor,
        'green': GreenColor,
        'brown': BrownColor,
        'blue': BlueColor,
        'magenta': MagentaColor,
        'cyan': CyanColor,
        'white': WhiteColor,
        'gray': GrayColor,
        'yellow': YellowColor,
        'smoke': SmokeColor,
        'default': WhiteColor,
    }

    BG_COLORS = {
        'black': BlackColor,
        'red': RedColor,
        'green': GreenColor,
        'brown': BrownColor,
        'blue': BlueColor,
        'magenta': MagentaColor,
        'cyan': CyanColor,
        'white': WhiteColor,
        'gray': GrayColor,
        'yellow': YellowColor,
        'smoke': SmokeColor,
        'default': BlackColor,
    }

    RENDER_INTERVAL = 0.1

    def __init__(self, screen, terminal, debug=False):
        self.screen = screen
        self.terminal = terminal
        self.debug = debug
        self.logger = logging.getLogger('StaSh.SequentialRenderer')
        self.last_rendered_time = 0
        self.render_thread = None

    @staticmethod
    def _same_style(char1, char2):
        return char1.fg == char2.fg \
               and char1.bg == char2.bg \
               and char1.bold is char2.bold \
               and char1.italics is char2.italics \
               and char1.underscore is char2.underscore \
               and char1.strikethrough is char2.strikethrough

    def _get_font(self, attrs):
        if attrs.bold and attrs.italics:
            return self.terminal.bold_italic_font
        elif attrs.bold:
            return self.terminal.bold_font
        elif attrs.italics:
            return self.terminal.italic_font
        else:
            return self.terminal.default_font

    def _build_attributes(self, attrs):
        return {
            'NSColor': self.FG_COLORS.get(attrs.fg, WhiteColor),
            'NSBackgroundColor': self.BG_COLORS.get(attrs.bg, BlackColor),
            'NSFont': self._get_font(attrs),
            'NSUnderline': 1 if attrs.underscore else 0,
            'NSStrikethrough': 1 if attrs.strikethrough else 0,
        }

    def _build_attributed_string(self, chars):
        """
        Build attributed text in a more efficient way than char by char.
        It groups characters with the same attributes and apply the attributes
        to them at once.
        :param [ShChar] chars: A list of ShChar upon which the attributed text is built.
        :rtype: object
        """
        # Initialize a string with default attributes
        attributed_text = NSMutableAttributedString.alloc().initWithString_attributes_(
            ''.join(char.data for char in chars),
            self._build_attributes(DEFAULT_CHAR),
        ).autorelease()

        prev_char = chars[0]
        location = length = 0
        for idx, curr_char in enumerate(chars):
            length += 1
            if not self._same_style(prev_char, curr_char):  # a group is found
                if not self._same_style(prev_char, DEFAULT_CHAR):  # skip default attrs
                    attributed_text.setAttributes_range_(
                        self._build_attributes(prev_char),
                        (location, length - 1)
                    )
                length = 1
                location = idx
                prev_char = curr_char

            if idx == len(chars) - 1:  # last char
                if not self._same_style(prev_char, DEFAULT_CHAR):
                    attributed_text.setAttributes_range_(
                        self._build_attributes(prev_char),
                        (location, length)
                    )

        return attributed_text

    def render(self, no_wait=False):
        """
        Render the screen buffer to the UITextView. Normally the rendering process
        is delayed to throttle the total attempts of rendering.
        :param bool no_wait: Immediately render the screen without delay.
        """
        # The last_rendered_time is useful to ensure that the first rendering
        # is not delayed.
        if time() - self.last_rendered_time > self.RENDER_INTERVAL or no_wait:
            if self.render_thread is not None:
                self.render_thread.cancel()
            self._render()
        else:  # delayed rendering
            if self.render_thread is None or not self.render_thread.isAlive():
                self.render_thread = sh_delay(self._render, self.RENDER_INTERVAL)
            # Do nothing if there is already a delayed rendering thread waiting

    @on_main_thread
    def _render(self):
        # This must run on the main UI thread. Otherwise it crashes.

        self.last_rendered_time = time()

        # Lock screen to get atomic information
        with self.screen.acquire_lock():
            intact_left_bound, intact_right_bound = self.screen.get_bounds()
            screen_buffer_length = len(self.screen.buffer)
            cursor_x = self.screen.cursor_x
            renderable_chars = self.screen.renderable_chars
            self.screen.clean()

        if IN_PYTHONISTA:

            # Specific code for ios 8 to fix possible crash
            if ON_IOS_8:
                tvo_texts = NSMutableAttributedString.alloc().initWithAttributedString_(
                    self.terminal.tvo.attributedText()).autorelease()
            else:
                tvo_texts = self.terminal.tso
                tvo_texts.beginEditing()  # batch the changes

            # First remove any leading texts that are rotated out
            if intact_left_bound > 0:
                tvo_texts.replaceCharactersInRange_withString_(
                    (0, intact_left_bound),
                    ''
                )

            tv_text_length = tvo_texts.length()

            # Second (re)render any modified trailing texts
            # When there are contents beyond the right bound, either on screen
            # or on terminal, the contents need to be re-rendered.
            if intact_right_bound < max(tv_text_length, screen_buffer_length):
                if len(renderable_chars) > 0:
                    tvo_texts.replaceCharactersInRange_withAttributedString_(
                        (intact_right_bound,
                         tv_text_length - intact_right_bound),
                        self._build_attributed_string(renderable_chars)
                    )
                else:  # empty string, pure deletion
                    tvo_texts.replaceCharactersInRange_withString_(
                        (intact_right_bound,
                         tv_text_length - intact_right_bound),
                        ''
                    )

            if ON_IOS_8:
                self.terminal.tvo.setAttributedText_(tvo_texts)  # set the text
            else:
                tvo_texts.endEditing()  # end of batched changes

            # Set the cursor position
            self.terminal.selected_range = (cursor_x, cursor_x)

            # Ensure cursor line is visible by scroll  to the end of the text
            self.terminal.scroll_to_end()

        else:  # For debugging on PC
            self.terminal.text = self.screen.text