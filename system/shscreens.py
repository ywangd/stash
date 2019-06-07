# coding: utf-8
"""
In-memory screen related code.
"""
import itertools
import logging
import threading
from collections import deque, namedtuple
from contextlib import contextmanager
from time import time

from six.moves import xrange

# noinspection PyPep8Naming
from .shcommon import IN_PYTHONISTA, ON_IOS_8
from .shcommon import Graphics as graphics
from .shcommon import sh_delay

try:
    from objc_util import *
except ImportError:
    from .dummyobjc_util import *



NSMutableAttributedString = ObjCClass('NSMutableAttributedString')
UIFont = ObjCClass('UIFont')

BlackColor = UIColor.blackColor()
RedColor = UIColor.redColor()
GreenColor = UIColor.greenColor()
BrownColor = UIColor.brownColor()
BlueColor = UIColor.blueColor()
# BlueColor = UIColor.colorWithRed_green_blue_alpha_(0.3, 0.3, 1.0, 1.0)
MagentaColor = UIColor.magentaColor()
CyanColor = UIColor.cyanColor()
WhiteColor = UIColor.whiteColor()
GrayColor = UIColor.grayColor()
# GrayColor = UIColor.colorWithRed_green_blue_alpha_(0.5, 0.5, 0.5, 1.0)
YellowColor = UIColor.yellowColor()
# SmokeColor = UIColor.smokeColor()
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
DEFAULT_LINE = itertools.repeat(DEFAULT_CHAR)

def take(n, iterable):
    return list(itertools.islice(iterable, n))

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

        self._buffer = deque()  # buffer to hold chars
        self.lock = threading.Lock()

        self.attrs = ShChar(' ')

        self.reset()

    def reset(self, *args):  # *args is a necessary placeholder
        """
        Clear the screen and reset its state.
        *args is needed because dispatch from stream always call handlers
        with at least one parameter (even it is a dummy 0).
        """
        # Empty the buffer
        self._buffer.clear()

        # The cursor position
        self.cursor_xs = self.cursor_xe = 0

        # This is the location where modifiable chars start. It is immediately
        # after where latest program write ends. This property is used to calculate
        # modifiable range and is really only useful for User side actions.
        self.x_drawend = 0

        # The left and right bounds are helpers to renderer for performance.
        # Only texts outside of the bounds get rebuilt and re-rendered.
        # All chars before this location must be removed from terminal text.
        # Note this value is relative to start of Terminal text.
        self.intact_left_bound = 0
        # All chars after this location must be re-rendered. Note this value is
        # relative to start of the Screen's buffer.
        self.intact_right_bound = 0

        self.nlines = 0

    @property
    def cursor_x(self):
        """
        Note this method returns both bounds of cursor as a tuple.
        :rtype: (int, int)
        """
        return self.cursor_xs, self.cursor_xe

    @cursor_x.setter
    def cursor_x(self, value):
        """
        This method sets both bounds of the cursor to the same value.
        :param int value: New value for both bounds of the cursor
        :return:
        """
        self.cursor_xs = self.cursor_xe = value

    @property
    def text(self):
        """
        :rtype: str
        """
        return ''.join(c.data for c in self._buffer)

    @property
    def text_length(self):
        """
        :rtype: int
        """
        return len(self._buffer)

    @property
    def renderable_chars(self):
        """
        Trailing characters that need to be re-rendered (this is not the same
        as modifiable chars).
        Note this return a list of ShChar not a String.
        :rtype: [ShChar]
        """
        _, rbound = self.get_bounds()
        return [self._buffer[x] for x in xrange(rbound, len(self._buffer))]

    @property
    def x_modifiable(self):
        """
        The location where characters start to be modifiable by users. The value
        is relative to the beginning of screen buffer.
        :rtype: int
        """
        # The position is either the x_drawend or last LF location plus one,
        # whichever is larger.
        for idx in xrange(self.text_length - 1, self.x_drawend - 1, -1):
            if self._buffer[idx].data == '\n':
                return idx + 1
        else:
            return self.x_drawend

    @property
    def modifiable_range(self):
        """
        The range of modifiable characters. Values are relative to the
        beginning of screen buffer.
        :rtype: (int, int)
        """
        return self.x_modifiable, self.text_length

    @property
    def modifiable_string(self):
        """
        A string represents the characters that are in the modifiable range.
        :rtype: str
        """
        return ''.join(self._buffer[idx].data for idx in xrange(*self.modifiable_range))

    @modifiable_string.setter
    def modifiable_string(self, s):
        """
        Set the modifiable_string to the given string using default Char properties.
        This method is only called by UI delegate side, i.e. NOT running scripts.
        :param str s: A new value for modifiable_string.
        """
        self.replace_in_range(self.modifiable_range, s)

    @contextmanager
    def acquire_lock(self, blocking=True):
        """
        Lock the screen for modification so that it will not be corrupted.
        :param blocking: By default the method blocks until a lock is acquired.
        """
        locked = self.lock.acquire(blocking)
        try:
            yield locked
        finally:
            if locked:
                self.lock.release()

    @contextmanager
    def buffer_rotate(self, n):
        """
        This method is used for when operations like replacing, insertion, deletion
        are needed in the middle of the character buffer.
        :param n:
        :return:
        """
        self._buffer.rotate(n)
        try:
            yield
        finally:
            self._buffer.rotate(-n)

    def get_bounds(self):
        """
        Get the left and right intact bounds of the screen buffer.
        The bounds could become negative if entire screen is flushed out before
        any rendering. In this case, the bounds need to be adjusted accordingly.
        :rtype (int, int):
        """
        rbound = self.intact_right_bound if self.intact_right_bound >= 0 else 0
        lbound = self.intact_left_bound if rbound > 0 else 0
        return lbound, rbound

    def clean(self):
        """
        Mark everything as rendered.
        """
        self.intact_left_bound = 0
        self.intact_right_bound = len(self._buffer)

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
            rng = (len(self._buffer), len(self._buffer))

        elif relative_to_x_modifiable:  # Convert to absolute location if necessary
            rng = rng[0] + self.x_modifiable, rng[1] + self.x_modifiable

        # Update the right bound if necessary
        if rng[0] < self.intact_right_bound:
            self.intact_right_bound = rng[0]

        rotate_n = max(len(self._buffer) - rng[1], 0)
        self._buffer.rotate(rotate_n)  # rotate buffer first so deletion is possible
        try:
            if rng[0] != rng[1]:  # delete chars if necessary
                self._pop_chars(rng[1] - rng[0])
            # The newly inserted chars are always of default properties
            self._buffer.extend(DEFAULT_CHAR._replace(data=c) for c in s)

        finally:
            self._buffer.rotate(-rotate_n)

        # Update cursor to the end of this replacement
        self.cursor_x = rng[0] + len(s)

        # Normally the draw end is not set
        if set_drawend:
            self.x_drawend = self.cursor_xs

        nlf = s.count('\n')
        if nlf > 0:  # ensure max number of lines is kept
            self.nlines += nlf
            self._ensure_nlines_max()

    def _pop_chars(self, n=1):
        """
        Remove number of given characters form the right END of the buffer
        :param n:
        :return:
        """
        for _ in xrange(n):
            self._buffer.pop()
        if self.text_length < self.intact_right_bound:
            self.intact_right_bound = self.text_length

    def _ensure_nlines_max(self):
        """
        Keep number of lines under control
        """
        char_count = line_count = 0
        for _ in xrange(self.nlines_max, self.nlines):
            # Remove the top line
            for idx in xrange(self.text_length):
                char_count += 1
                if self._buffer.popleft().data == '\n':
                    line_count += 1
                    break

        if char_count > 0:
            self.intact_left_bound += char_count
            self.intact_right_bound -= char_count
            self.cursor_xs -= char_count
            self.cursor_xe -= char_count
            self.x_drawend -= char_count

        if line_count > 0:
            self.nlines -= line_count

    def _rfind_nth_nl(self, from_x=None, n=1, default=None):
        if from_x is None:
            from_x = self.cursor_xs
        for idx in xrange(from_x, -1, -1):
            try:  # try for when from_x is equal to buffer length (i.e. at the end of the buffer)
                if self._buffer[idx].data == '\n':
                    n -= 1
                    if n == 0:
                        return idx
            except IndexError:
                pass
        else:
            return default
                
    def _find_nth_nl(self, from_x=None, n=1, default=None):
        if from_x is None:
            from_x = self.cursor_xs
        for idx in xrange(from_x, self.text_length):
            try:
                if self._buffer[idx].data == '\n':
                    n -= 1
                    if n == 0:
                        return idx
            except IndexError:
                pass
        else:
            return default

    # noinspection PyProtectedMember
    def draw(self, c):
        """
        Add given char to the right end of the buffer and update the last draw
        location. This method should ONLY be called by ShStream.
        :param str c: A new character to draw
        """

        if self.cursor_xs == self.text_length:  # cursor is at the end
            if self.text_length < self.intact_right_bound:
                self.intact_right_bound = self.text_length
            self._buffer.append(self.attrs._replace(data=c))
            self.cursor_x = self.x_drawend = self.text_length

        else:  # cursor is in the middle
            # First rotate the text is that to the right of cursor
            with self.buffer_rotate(self.text_length - self.cursor_xs - 1):
                # Remove the character at the cursor and append new character
                # This is effectively character REPLACING operation
                c_poped = self._buffer.pop()
                self._buffer.append(self.attrs._replace(data=c))
                # The replacing must be within a single line, so the newline
                # character cannot be replaced and instead a new char is inserted
                # right before the newline.
                # Also when the new character is a newline, it is effectively an
                # insertion NOT replacement (i.e. it pushes everything following
                # it to the next line).
                if c == '\n' or c_poped.data == '\n':
                    self._buffer.append(c_poped)
                # Update the cursor and drawing end
                self.cursor_x = self.x_drawend = self.cursor_xs + 1
                # Update the intact right bound
                if self.x_drawend < self.intact_right_bound:
                    self.intact_right_bound = self.x_drawend

        # Count the number of lines
        if c == '\n':
            self.nlines += 1
            self._ensure_nlines_max()

    def backspace(self):
        """
        Move cursor back one character. Do not cross lines.
        """
        cursor_xs = self.cursor_xs - 1
        try:
            if self._buffer[cursor_xs] != '\n':
                self.cursor_x = cursor_xs
        except IndexError:
            self.cursor_x = 0

    def carriage_return(self):
        """
        Process \r to move cursor to the beginning of the current line.
        """
        self.cursor_x = self._rfind_nth_nl(default=-1) + 1

    def delete_characters(self, count=0):
        """
        Delete n characters from cursor including cursor within the current line.
        :param count: If count is 0, delete till the next newline.
        """
        if self.cursor_xs == self.text_length or self._buffer[self.cursor_xs] == '\n':
            return
        if count == 0:  # delete till the next newline
            count = self.text_length
        with self.buffer_rotate(-self.cursor_xs):
            for _ in xrange(min(count, self.text_length - self.cursor_xs)):
                c = self._buffer.popleft()
                if c.data == '\n':  # do not delete newline
                    self._buffer.appendleft(c)
                    break
            self.x_drawend = self.cursor_xs
            if self.x_drawend < self.intact_right_bound:
                self.intact_right_bound = self.x_drawend

    def erase_in_line(self, mode=0):
        """
        Erase a line with different mode. Note the newline character is NOT deleted.
        :param mode:
        :return:
        """
        # Calculate the range for erase
        if mode == 0:  # erase from cursor to end of line, including cursor
            rng = [self.cursor_xs, self._find_nth_nl(default=self.text_length)]
            try:  # do not include the newline character
                if self._buffer[rng[0]] == '\n':
                    rng[0] += 1
            except IndexError:
                pass

        elif mode == 1:  # erase form beginning of line to cursor, including cursor
            rng = [self._rfind_nth_nl(default=-1) + 1, min(self.cursor_xs + 1, self.text_length)]
            try:
                if self._buffer[rng[1] - 1] == '\n':
                    rng[1] -= 1
            except IndexError:
                pass

        else:  # mode == 2:  # erase the complete line
            rng = [self._rfind_nth_nl(default=-1) + 1, self._find_nth_nl(default=self.text_length)]

        # fast fail when there is nothing to erase
        if rng[0] >= rng[1]:
            return

        # Erase characters in the range
        with self.buffer_rotate(self.text_length - rng[1]):
            for _ in xrange(*rng):
                self._buffer.pop()
            self._buffer.extend(take(rng[1] - rng[0], DEFAULT_LINE))
            self.x_drawend = rng[0]
            # update the intact right bound
            if self.x_drawend < self.intact_right_bound:
                self.intact_right_bound = self.x_drawend

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
        
    def load_pyte_screen(self, pyte_screen):
        """
        This method is for command script only, e.g. ssh.
        """

        with self.acquire_lock():

            self.intact_left_bound = 0
            nlines, ncolumns = pyte_screen.lines, pyte_screen.columns

            line_count = 0
            column_count = 0
            for line in reversed(pyte_screen.display):
                line = line.rstrip()
                if line != '':
                    column_count = len(line)
                    break
                line_count += 1

            nchars_pyte_screen = (nlines - line_count - 1) * (ncolumns + 1) + column_count

            idx_cursor_pyte_screen = pyte_screen.cursor.x + pyte_screen.cursor.y * (ncolumns + 1)

            if nchars_pyte_screen < idx_cursor_pyte_screen:
                nchars_pyte_screen = idx_cursor_pyte_screen

            try:
                min_idx_dirty_line = min(pyte_screen.dirty)
            except ValueError:
                min_idx_dirty_line = 0

            idx_dirty_char = (ncolumns + 1) * min_idx_dirty_line

            # self.logger.info(
            #     'min_idx_dirty_line={}, idx_dirty_char={}, nchars_pyte_screen={}, self.text_length={}'.format(
            #         min_idx_dirty_line, idx_dirty_char, nchars_pyte_screen, self.text_length
            #     )
            # )

            if idx_dirty_char > self.text_length - 1:
                self.intact_right_bound = self.text_length
            else:
                self.intact_right_bound = min(self.text_length, nchars_pyte_screen)
                for idx in xrange(idx_dirty_char, nchars_pyte_screen):
                    # self.logger.info('idx = %s' % idx)
                    if idx >= self.text_length:
                        break
                    idx_line, idx_column = idx / (ncolumns + 1), idx % (ncolumns + 1)
                    if idx_column == ncolumns:
                        continue
                    pyte_char = pyte_screen.buffer[idx_line][idx_column]
                    # self.logger.info('HERE = %s' % idx)
                    if self._buffer[idx].data != pyte_char.data \
                            or not ShSequentialRenderer._same_style(self._buffer[idx], pyte_char):
                        # self.logger.info('breaking %s' % idx)
                        self.intact_right_bound = idx
                        break

            for _ in xrange(self.intact_right_bound, self.text_length):
                self._buffer.pop()

            for idx in xrange(self.intact_right_bound, nchars_pyte_screen):
                idx_line, idx_column = idx / (ncolumns + 1), idx % (ncolumns + 1)
                if idx_column != ncolumns:
                    c = pyte_screen.buffer[idx_line][idx_column]
                    self._buffer.append(ShChar(**c._asdict()))
                else:
                    self._buffer.append(ShChar('\n'))

            self.cursor_x = idx_cursor_pyte_screen

        # self.logger.info('intact_right_bound={}, cursor={}'.format(self.intact_right_bound, self.cursor_xs))
        # self.logger.info('|%s|' % pyte_screen.display)
        # self.logger.info('text=|%s|' % self.text)
        # self.logger.info('text_length=%s' % self.text_length)


class ShSequentialRenderer(object):

    """
    A specific renderer for `ShSequentialScreen`. It does its job by
    building texts from the in-memory screen and insert them to the
    UI terminal.

    :param ShSequentialScreen screen: In memory screen
    :param ShTerminal terminal: The real UI terminal
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
        
        # update default colors to match terminal
        self.FG_COLORS["default"] = self.FG_COLORS.get(self.terminal.text_color, WhiteColor)
        self.BG_COLORS["default"] = self.BG_COLORS.get(self.terminal.background_color, BlackColor)

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
            screen_buffer_length = self.screen.text_length
            cursor_xs, cursor_xe = self.screen.cursor_x
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

            # Set the cursor position. This makes terminal and main screen cursors in sync
            self.terminal.selected_range = (cursor_xs, cursor_xe)

            # Ensure cursor line is visible by scroll to the end of the text
            self.terminal.scroll_to_end()

        else:  # For debugging on PC
            self.terminal.text = self.screen.text