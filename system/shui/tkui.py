"""
Tkinter UI for StaSh
"""
import six
from six.moves import tkinter,  tkinter_messagebox, tkinter_scrolledtext, queue

from ..shscreens import ShChar
from ..shcommon import K_CC, K_CD, K_HUP, K_HDN, K_CU, K_TAB, K_HIST, K_CZ, K_KB
from .base import ShBaseUI, ShBaseTerminal, ShBaseSequentialRenderer


class ShUI(ShBaseUI):
    """
    An UI using the Tkinter module.
    """
    def __init__(self, *args, **kwargs):
        ShBaseUI.__init__(self, *args, **kwargs)
        # ui
        self.tk = tkinter.Tk()
        self.tk.title("StaSh")
        self.tk.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # terminal
        self.terminal = ShTerminal(self.stash, self)
    
    def show(self):
        self.tk.mainloop()
    
    def on_close(self):
        """
        Called when the window will be closed
        """
        if tkinter_messagebox.askokcancel(u"Quit", u"Are you sure you want to quit?"):
            self.tk.destroy()
            self.on_exit()


class ShTerminal(ShBaseTerminal):
    """
    A Terminal using the Tkinter module
    """
    
    _LOOP_DELAY = 5
    
    _keymapping = {  # tkinter event -> StaSh key
        "\x03": K_CC,    # ctrl-c
        "\t": K_TAB,     # tab
        "\x08": K_HIST,  # ctrl-h
        "\x1a": K_CZ,    # ctrl-z
        "\x15": K_CU,    # ctrl-u
        
    }
    
    def __init__(self, stash, parent):
        ShBaseTerminal.__init__(self, stash, parent)
        self._txtvar_out = tkinter.StringVar(self.parent.tk)
        self._txtvar_out.trace("w", self._update_text)
        self._txt = tkinter_scrolledtext.ScrolledText(
            self.parent.tk,
            wrap=tkinter.CHAR,
            bg=self._color_from_tuple(self.background_color),
            fg=self._color_from_tuple(self.text_color),
            insertbackground=self._color_from_tuple(self.tint_color),
            selectbackground=self._color_from_tuple(self.tint_color),
            )
        self._txt.pack(fill=tkinter.BOTH, expand=1)
        # binding
        self._txt.bind("<Key>", self._on_key_press)
        self._txt.bind("<FocusIn>", self._on_focus)
        self._txt.bind("<FocusOut>", self._on_focus)
        self._txt.bind("<Left>", self._arrow_key_pressed)
        self._txt.bind("<Right>", self._arrow_key_pressed)
        self._txt.bind("<Up>", self._arrow_key_pressed)
        self._txt.bind("<Down>", self._arrow_key_pressed)
        # we can not yet initialize the color system, so we need to do this later
        self._colors_initialized = False
        # output queue
        self._q = queue.Queue()
        self.parent.tk.after(self._LOOP_DELAY, self._loop)
    
    def _loop(self):
        try:
            v = self._q.get(0)
        except queue.Empty:
            pass
        else:
            self._txtvar_out.set(v)
        self.parent.tk.after(self._LOOP_DELAY, self._loop)
    
    @property
    def text(self):
        return self._txt.get("1.0", tkinter.END).replace("\r\n", "\n").replace("\r", "\n")[:-1]
    
    @text.setter
    def text(self, value):
        self._q.put(value)
    
    def _on_key_press(self, event):
        """
        Called when a key was pressed.
        :param event: the event which fired this callback
        :type event: six.moves.tkinter.Event
        """
        # get the current position
        cp = self._get_cursor_position()  # TODO: check if this must be calculated before or after the keypress
        rng = self.selected_range
        replacement = event.char
        skip_should_change = False  # if true, skip should_change
        if self.debug:
            self.logger.debug("key {!r} pressed (symbol: {!r}; selected: {!r})".format(replacement, event.keysym, rng))
        
        if replacement in ("\r", "\r\n"):
            replacement = "\n"
        elif replacement == "\x08" and event.keysym != "h":
            # backspace (for some reason, same code as ctrl-h)
            replacement = u""
            if rng[0] == rng[1]:
                rng = (rng[0] - 1, rng[1])
        elif replacement == "\x7f":
            # del
            replacement = u""
            skip_should_change = True
            if rng[0] == rng[1]:
                rng = (rng[0], rng[1])
        elif replacement in self._keymapping:
            self.parent.vk_tapped(self._keymapping[replacement])
            return "break"
        
        if skip_should_change or self.stash.user_action_proxy.tv_responder.textview_should_change(None, rng, replacement):
            self.parent.tk.after(0, self._notify_change)
            #self.parent.tk.after(0, self._notify_cursor_move)
        else:
            # break event
            return "break"
        # TODO: the cursor probably moved
    
    def _arrow_key_pressed(self, event):
        """
        Called when an arrow key was pressed.
        """
        d = event.keysym.lower()
        if d == "left":
            self.parent.arrowLeftAction()
        elif d == "right":
            self.parent.arrowRightAction()
        elif d == "up":
            self.parent.arrowUpAction()
        elif d == "down":
            self.parent.arrowDownAction()
        else:
            raise ValueError("Unknown key: {!r}".format(d))
        return "break"
    
    def _notify_change(self):
        """
        Notify StaSh that the text changed.
        """
        self.stash.user_action_proxy.tv_responder.textview_did_change(None)
    
    def _set_text(self, text):
        """
        Set the text.
        :param text: text to set
        :type text: str
        """
        self.text = text
        
    
    def _on_focus(self, event):
        """
        Called when the focus was lost.
        :param event: the event which fired this callback
        :type event: six.moves.tkinter.Event
        """
        self.stash.user_action_proxy.tv_responder.textview_did_begin_editing(None)
    
    def _on_focus_loss(self, event):
        """
        Called when the focus was lost.
        :param event: the event which fired this callback
        :type event: six.moves.tkinter.Event
        """
        self.stash.user_action_proxy.tv_responder.textview_did_end_editing(None)
    
    def _get_cursor_position(self):
        """
        Return the cursor position as a delta from the start.
        :return: the cursor position
        :rtype: int
        """
        v = self._get_absolute_cursor_position()
        return self._abs_cursor_pos_to_rel_pos(v)
    
    def _get_absolute_cursor_position(self):
        """
        Return the actual cursor position as a tuple of (row, column)
        :return: (row, column) of cursor
        :rtype: tuple of (int, int)
        """
        # source of first line: https://stackoverflow.com/questions/30000368/how-to-get-current-cursor-position-for-text-widget
        raw = self._txt.index(tkinter.INSERT)
        return self._tk_index_to_tuple(raw)
    
    def _abs_cursor_pos_to_rel_pos(self, value, lines=None):
        """
        Convert an absolute cursor position (tuple of (int, int)) into a index relative to the start (int).
        'lines' are optional and specify a list of lines on which these calculations should be made.
        :param value: value to convert
        :type value: tuple of (int, int)
        :param lines: alternative lines to calculate position from (default: current lines)
        :type lines: list of str
        """
        if lines is None:
            # get lines
            lines = self.text.split("\n")
        row, column = value
        n = 0
        # first, add all lines before the current one
        for i in range(row):
            line = lines[i]
            n += len(line) + 1  # 1 for linebreak
        # add column
        n += column
        # done
        return n
    
    def _rel_cursor_pos_to_abs_pos(self, value, lines=None):
        """
        Convert a cursor position relative to the start (int) to a tuple of (row, column).
        'lines' are optional and specify a list of lines on which these calculations should be made.
        :param value: value to convert
        :type value: int
        :param lines: alternative lines to calculate position from (default: current lines)
        :type lines: list of str
        """
        if lines is None:
            # get lines
            lines = self.text.split("\n")
        n = value
        row = 0
        while True:
            if row >= len(lines):
                # for some reason, we are at the end of the text. this is probably a bug, but lets return an approximate value to the end
                return (len(lines) - 1, len(lines[len(lines) - 1]) - 1 )
            ll = len(lines[row])
            if n <= ll:
                # n fits in line
                return row, n
            else:
                # n must be in next line
                n -= (ll + 1)  # 1 for newline
                row += 1
    
    def _tk_index_to_tuple(self, value):
        """
        Convert a tkinter index to a tuple of (row, column), starting at 0
        :param value: value to convert
        :type value: str
        :return: the converted value as (row, column), both starting at 0
        :rtype: tuple of (int, int)
        """
        splitted = value.split(".")
        row = int(splitted[0]) - 1
        column = int(splitted[1])
        return (row, column)
    
    def _tuple_to_tk_index(self, value):
        """
        Convert a (row, column) tuple to a tk index.
        :param value: value to convert
        :type value: tuple of (int, int)
        :return: the converted value
        :rtype: str
        """
        row, column = value
        return str(row + 1) + "." + str(column)
    
    def _get_selection_range(self):
        """
        Return the index of the currently selected text.
        :return: start and end index of the currently selected text
        :rtype: tuple of (int, int)
        """
        # based on: https://stackoverflow.com/questions/4073468/how-do-i-get-a-selected-string-in-from-a-tkinter-text-box
        # check if text is selected
        if not self._txt.tag_ranges(tkinter.SEL):
            return None, None
        raw_start = self._txt.index(tkinter.SEL_FIRST)
        raw_end = self._txt.index(tkinter.SEL_LAST)
        si = self._tk_index_to_tuple(raw_start)
        ei = self._tk_index_to_tuple(raw_end)
        rsi = self._abs_cursor_pos_to_rel_pos(si)
        rei = self._abs_cursor_pos_to_rel_pos(ei)
        return rsi, rei
    
    def _leftmost(self):
        """
        Check if the current cursor is at the left end of the modifiable chars.
        """
        return self._get_cursor_position() <= self.stash.main_screen.x_modifiable
        
    
    def _update_text(self, *args):
        """
        Update the text
        """
        self._txt.delete("1.0", tkinter.END)
        out = self._txtvar_out.get()
        self._txt.insert("1.0", out)
    
    def _tag_for_char(self, c):
        """
        Return the tag to use for the given character.
        :param c: character to get tag for
        :type c: stash.system.shscreens.ShChar
        :return: the tag used for this char
        :rtype: str
        """
        return self._tag_for_options(
            fg=c.fg,
            bg=c.bg,
            bold=c.bold,
            italics=c.italics,
            underscore=c.underscore,
            strikethrough=c.strikethrough,
            reverse=c.reverse,
            )
    
    def _tag_for_options(self,
            fg="default",
            bg="default",
            bold=False,
            italics=False,
            underscore=False,
            strikethrough=False,
            reverse=False,
            ):
        """
        Return a tag which described the given options.
        :param fg: fg color
        :type fg: str
        :bg: bg color
        :type bg: str
        :param bold: boldness
        :type bold: bool
        :param italics: toogle italics
        :type italics: bool
        :param underscore: toogle underscore
        :type underscore: bool
        :param striketrough: toogle striketrough
        :type striketrough: bool
        :param reverse: no idea
        :type reverse: bool
        :return: a tag which identifies this style
        :rtype: str
        """
        s = "{}-{}".format(fg, bg)
        if bold:
            s += "-bold"
        if italics:
            s += "italics"
        if underscore:
            s += "-underscore"
        if strikethrough:
            s += "-strikethrough"
        if reverse:
            s += "-reverse"
        return s
    
    def _add_color_tags(self):
        """
        Add the color tags.
        """
        # TODO: surely there is a better way of doing this.
        self.logger.info("Initializing color system...")
        for fg in self.stash.renderer.FG_COLORS:
            for bg in self.stash.renderer.BG_COLORS:
                for bold in (False, True):
                    for italics in (False, True):
                        for underscore in (False, True):
                            for strikethrough in (False, True):
                                # striketrough is implemented in replace_in_range()
                                for reverse in (False, True):
                                    # reverse does not actually seem to be used anywhere
                                    tag = self._tag_for_options(
                                        fg=fg,
                                        bg=bg,
                                        bold=bold,
                                        italics=italics,
                                        underscore=underscore,
                                        strikethrough=strikethrough,
                                        reverse=reverse,
                                        )
                                    kwargs = {}
                                    fontattrs = []
                                    if fg != "default":
                                        kwargs["foreground"] = self.stash.renderer.FG_COLORS[fg]
                                    if bg != "default":
                                        kwargs["background"] = self.stash.renderer.BG_COLORS[bg]
                                    if underscore:
                                        kwargs["underline"] = True
                                    if bold:
                                        fontattrs.append("bold")
                                    if italics:
                                        fontattrs.append("italic")
                                    font = ("Menlo-regular", self.font_size, " ".join(fontattrs))
                                    kwargs["font"] = font
                                    self._txt.tag_config(
                                        tag,
                                        **kwargs
                                        )
                                    # TODO: support for reverse
        self._colors_initialized = True
        self.logger.info("Color system initialized.")
    
    def _color_from_tuple(self, value):
        """
        Convert an rgb color tuple to a hex color
        :param value: value to convert
        :type value: tuple of (int, int, int)
        :return: hexcode of color
        :rtype: str
        """
        r, g, b = value
        r = int(255 * r)
        g = int(255 * g)
        b = int(255 * b)
        hexcode = "#{:02X}{:02X}{:02X}".format(r, g, b)
        return hexcode
    
    # ============= api implementation ============
    
    @property
    def selected_range(self):
        start, end = self._get_selection_range()
        if (start is None) or (end is None):
            cp = self._get_cursor_position()
            return (cp, cp)
        else:
            return (start, end)
    
    @selected_range.setter
    def selected_range(self, value):
        assert isinstance(value, tuple)
        assert len(value) == 2
        assert isinstance(value[0], int) and isinstance(value[1], int)
        if value == self.selected_range:
            # do nothing
            pass
        else:
            # set cursor synced to false
            self.cursor_synced = False
            # set tag
            start = self._tuple_to_tk_index(self._rel_cursor_pos_to_abs_pos(value[0]))
            end = self._tuple_to_tk_index(self._rel_cursor_pos_to_abs_pos(value[1]))
            self._txt.tag_add(tkinter.SEL, start, end)
            self._txt.mark_set(tkinter.INSERT, end)
            # set focus
            self.set_focus()
    
    def scroll_to_end(self):
        self._txt.see(tkinter.END)
    
    def set_focus(self):
        self._txt.focus_set()
    
    def lose_focus(self):
        self.parent.tk.focus_set()
    
    def replace_in_range(self, rng, text):
        """
        Replace the text in the given range
        :param rng: range to replace (start, length)
        :type rng: tuple of (int, int)
        :param text: text to insert
        :type text: iterable of str or ShChar
        """
        rstart, length = rng
        start, end = self._rel_cursor_pos_to_abs_pos(rstart), self._rel_cursor_pos_to_abs_pos(rstart + length)
        tkstart, tkend = self._tuple_to_tk_index(start), self._tuple_to_tk_index(end)
        saved = self.selected_range
        self._txt.delete(tkstart, tkend)
        cp = rstart
        for c in text:
            a = 1
            ctkp = self._tuple_to_tk_index(self._rel_cursor_pos_to_abs_pos(cp))
            if isinstance(c, (six.binary_type, six.text_type)):
                self._txt.insert(ctkp, c)
            elif isinstance(c, ShChar):
                if not self._colors_initialized:
                    self._add_color_tags()
                ch = c.data
                if c.strikethrough:
                    ch = u"\u0336" + ch
                    a += 1
                self._txt.insert(ctkp, ch, self._tag_for_char(c))
            else:
                raise TypeError("Unknown character type {!r}!".format(type(c)))
            cp += a
        self.selected_range = saved  # restore cursor position


class ShSequentialRenderer(ShBaseSequentialRenderer):
    """
    ShSequentialBaseRenderer for Tkinter
    """
    RENDER_INTERVAL = 1
    
    FG_COLORS = {
        'black': "black",
        'red': "red",
        'green': "green",
        'brown': "brown",
        'blue': "blue",
        'magenta': "magenta",
        'cyan': "cyan",
        'white': "white",
        'gray': "gray",
        'yellow': "yellow",
        'smoke': "gray64",
        'default': "white",
    }

    BG_COLORS = {
        'black': "black",
        'red': "red",
        'green': "green",
        'brown': "brown",
        'blue': "blue",
        'magenta': "magenta",
        'cyan': "cyan",
        'white': "white",
        'gray': "gray",
        'yellow': "yellow",
        'smoke': "gray64",
        'default': "red",
    }
    
    def __init__(self, *args, **kwargs):
        ShBaseSequentialRenderer.__init__(self, *args, **kwargs)
        self.should_render = False
        self.stash.ui.tk.after(0, self._renderer_loop)
    
    def _renderer_loop(self):
        """
        Internal renderer loop.
        """
        if self.should_render:
            self.should_render = False
            self._render()
        self.stash.ui.tk.after(self.RENDER_INTERVAL, self._renderer_loop)
    
    def render(self, no_wait=False):
        self.should_render = True
    
    def _render(self, no_wait=False):
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
