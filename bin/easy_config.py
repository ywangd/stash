"""a graphical config manager for StaSh"""
import os
import ast
import threading
import imp
import console
import ui
from stash.system.shcommon import _STASH_CONFIG_FILES, _STASH_ROOT


_stash = globals()["_stash"]

ORIENTATIONS = ("landscape", "landscape_left", "landscape_right")
PAA_PATH= os.path.join(
		_STASH_ROOT,
		"lib/pythonista_add_action.py"
		)

# define option types
TYPE_BOOL = 1
TYPE_INT = 2
TYPE_STR = 3
TYPE_FILE = 4  # NotImplemented
TYPE_COLOR = 5
TYPE_CHOICE = 6
TYPE_LABEL = 7
TYPE_COMMAND = 9

CONFIG_PATH = os.path.join(
	os.getenv("STASH_ROOT"),  # not using shcommons._STASH_ROOT here
	_STASH_CONFIG_FILES[0],
	)

# define functions for commands


@ui.in_background
def visit_homepage():
	"""opens the StaSh homepage."""
	mv = cfg_view  # [global] the main view
	mv.subview_open = True
	v = ui.WebView()
	v.present()
	v.load_url("https://www.github.com/ywangd/stash/")
	v.wait_modal()
	mv.subview_open = False


@ui.in_background
def add_editor_action():
	"""
	adds an editor action to the 'wrench' menu in the editor which
	launches launch_stash.py
	"""
	mv = cfg_view  # [global] the main view
	mv.ai.start()
	try:
		try:
			paa = imp.load_source("paa", PAA_PATH)
		except IOError:
			# install paa
			# we should not do this on module-level to improve
			# offline capatibility
			install_paa()
			paa = imp.load_source("paa", PAA_PATH)
		lsp = "/launch_stash.py"  # TODO: auto-detect
		paa.add_action(
			lsp,
			"monitor",
			"000000",
			"StaSh",
			)
		paa.save_defaults()
	finally:
		mv.ai.stop()

# define all options as a dict of:
#	section -> list of dicts of
#		display_name: str
#		option_name: str
#		type: int

OPTIONS = {
	"system": [
		{
			"display_name": "Resource File",
			"option_name": "rcfile",
			"type": TYPE_STR,
		},
		{
			"display_name": "Show Traceback",
			"option_name": "py_traceback",
			"type": TYPE_BOOL,
		},
		{
			"display_name": "Enable Debugger",
			"option_name": "py_pdb",
			"type": TYPE_BOOL,
		},
		{
			"display_name": "Encode Input as UTF-8",
			"option_name": "ipython_style_history_search",
			"type": TYPE_BOOL,
		},
		{
			"display_name": "Thread Type",
			"option_name": "thread_type",
			"type": TYPE_CHOICE,
			"choices": ("ctypes", "traced"),
		},
		],
	"display":
		[
		{
			"display_name": "Font Size",
			"option_name": "TEXT_FONT_SIZE",
			"type": TYPE_INT,
		},
		{
			"display_name": "Button Font Size",
			"option_name": "BUTTON_FONT_SIZE",
			"type": TYPE_INT,
		},
		{
			"display_name": "Background Color",
			"option_name": "BACKGROUND_COLOR",
			"type": TYPE_COLOR,
		},
		{
			"display_name": "Text Color",
			"option_name": "TEXT_COLOR",
			"type": TYPE_COLOR,
		},
		{
			"display_name": "Tint Color",
			"option_name": "TINT_COLOR",
			"type": TYPE_COLOR,
		},
		{
			"display_name": "Indicator Style",
			"option_name": "INDICATOR_STYLE",
			"type": TYPE_CHOICE,
			"choices": (
				"default",
				"black",
				"white",
				),
		},
		{
			"display_name": "Max History Length",
			"option_name": "HISTORY_MAX",
			"type": TYPE_INT,
		},
		{
			"display_name": "Max Buffer",
			"option_name": "BUFFER_MAX",
			"type": TYPE_INT,
		},
		{
			"display_name": "Max Autocompletion",
			"option_name": "AUTO_COMPLETION_MAX",
			"type": TYPE_INT,
		},
		{
			"display_name": "Virtual Keys",
			"option_name": "VK_SYMBOLS",
			"type": TYPE_STR,
		},
		],
	"StaSh": [
		{
			"display_name": "Version",
			"option_name": None,
			"type": TYPE_LABEL,
			"value": _stash.__version__,
		},
		{
			"display_name": "Update",
			"option_name": None,
			"type": TYPE_COMMAND,
			"command": "selfupdate",
		},
		{
			"display_name": "Create Editor Shortcut",
			"option_name": None,
			"type": TYPE_COMMAND,
			"command": add_editor_action,
		},
		{
			"display_name": "Visit Homepage",
			"option_name": None,
			"type": TYPE_COMMAND,
			"command": visit_homepage,
		},
		],
}

# section order
SECTIONS = [
	"StaSh",
	"system",
	"display",
	]


def install_paa():
	"""
	installs https://gist.github.com/jsbain/c9f42c81c53b276b6560.
	The name is changed to reduce a chance of a naming-conflict.
	"""
	url = "https://gist.github.com/jsbain/c9f42c81c53b276b6560/raw/"
	env = os.environ
	cmd = "wget -o {p} {url}".format(url=url, p=PAA_PATH)
	_stash(cmd, add_to_history=False)
	

class ColorPicker(object):
	"""
	This object will prompt the user for a color.
	Parts of this are copied from the pythonista examples.
	TODO: rewrite as a subclass of ui.View()
	"""
	def __init__(self, default=(0.0, 0.0, 0.0)):
		self.r, self.g, self.b, = default
		self.view = ui.View()
		self.view.background_color = "#ffffff"
		self.rslider = ui.Slider()
		self.rslider.continuous = True
		self.rslider.value = default[0]
		self.rslider.tint_color = "#ff0000"
		self.gslider = ui.Slider()
		self.gslider.continuous = True
		self.gslider.value = default[1]
		self.gslider.tint_color = "#00ff00"
		self.bslider = ui.Slider()
		self.bslider.continuous = True
		self.bslider.value = default[2]
		self.bslider.tint_color = "#0000ff"
		self.preview = ui.View()
		self.preview.background_color = self.rgb
		self.preview.border_width = 1
		self.preview.border_color = "#000000"
		self.preview.corner_radius = 5
		self.rslider.action = self.gslider.action = self.bslider.action = self.slider_action
		self.colorlabel = ui.Label()
		self.colorlabel.text = self.hexcode
		self.colorlabel.alignment = ui.ALIGN_CENTER
		self.view.add_subview(self.rslider)
		self.view.add_subview(self.gslider)
		self.view.add_subview(self.bslider)
		self.view.add_subview(self.preview)
		self.view.add_subview(self.colorlabel)
		w = self.view.width / 2.0
		self.preview.width = w - (w / 10.0)
		self.preview.x = w / 10.0
		hd = self.view.height / 10.0
		self.preview.height = (self.view.height / 3.0) * 2.0 - (hd * 2)
		self.preview.y = hd
		self.preview.flex = "BRWH"
		self.colorlabel.x = self.preview.x
		self.colorlabel.y = (hd * 2) + self.preview.height
		self.colorlabel.height = (self.view.height / 3.0) * 2.0 - (hd * 2)
		self.colorlabel.width = self.preview.width
		self.colorlabel.flex = "BRWH"
		self.rslider.x = self.gslider.x = self.bslider.x = w * 1.1
		self.rslider.width = self.gslider.width = self.bslider.width = w * 0.8
		self.rslider.flex = self.gslider.flex = self.bslider.flex = "LWHTB"
		h = self.view.height / 9.0
		self.rslider.y = h * 2
		self.gslider.y = h * 4
		self.bslider.y = h * 6
		self.rslider.height = self.gslider.height = self.bslider.height = h
	
	def slider_action(self, sender):
		"""called when a slider was moved"""
		self.r = self.rslider.value
		self.g = self.gslider.value
		self.b = self.bslider.value
		self.preview.background_color = self.rgb
		self.colorlabel.text = self.hexcode
	
	@property
	def hexcode(self):
		"""returns the selected color as a html-like hexcode"""
		hexc = "#%.02X%.02X%.02X" % self.rgb_255
		return hexc
	
	@property
	def rgb(self):
		"""
		returns the selected color as a tuple line (1.0, 1.0, 1.0)
		"""
		return (self.r, self.g, self.b)
	
	@property
	def rgb_255(self):
		"""
		returns the selected color as a rgb tuple like (255, 255, 255)
		"""
		r, g, b = self.rgb
		return (r * 255, g * 255, b * 255)
	
	def get_color(self):
		"""
		shows the view, wait until it is closed and the. return the selected color.
		"""
		self.view.present(
			"sheet",
			orientations=ORIENTATIONS,
			)
		self.view.wait_modal()
		return self.rgb


class ConfigView(ui.View):
	"""
	The main GUI.
	"""
	def __init__(self):
		ui.View.__init__(self)
		self.background_color = "#ffffff"
		self.table = ui.TableView()
		self.table.delegate = self.table.data_source = self
		self.table.flex = "WH"
		self.add_subview(self.table)
		self.ai = ui.ActivityIndicator()
		self.ai.style = ui.ACTIVITY_INDICATOR_STYLE_WHITE_LARGE
		self.ai.hides_when_stopped = True
		self.ai.x = self.width / 2.0 - (self.ai.width / 2.0)
		self.ai.y = self.height / 2.0 - (self.ai.height / 2.0)
		self.ai.flex = "LRTB"
		self.ai.background_color = "#000000"
		self.ai.alpha = 0.7
		self.ai.corner_radius = 5
		self.add_subview(self.ai)
		self.subview_open = False
		self.cur_tf = None
		self.hide_kb_button = ui.ButtonItem(
			"Hide Keyboard",
			action=self.hide_keyboard,
			enabled=False,
			)
		self.right_button_items = (self.hide_kb_button,)
	
	def show(self):
		"""shows the view and starts a thread."""
		self.present(orientations=ORIENTATIONS)
		# launch a background thread
		# we can not use ui.in_background here
		# because some dialogs would not open anymoe
		thr = threading.Thread(target=self.show_messages)
		thr.daemon = True
		thr.start()
	
	def show_messages(self):
		"""shows some warnings and tips."""
		console.alert(
			"Info",
			"If StaSh does not launch anymore after you changed the config, run the 'launch_stash.py' script with \n'--no-cfgfile'.",
			"Ok",
			hide_cancel_button=True,
			)
		while True:
			self.wait_modal()
			if not self.subview_open:
				break
		console.alert(
			"Info",
			"Some changes may only be visible after restarting StaSh and/or Pythonista.",
			"Ok",
			hide_cancel_button=True,
			)
	
	# data source and delegate functions. see docs
	
	def tableview_number_of_sections(self, tv):
		return len(SECTIONS)
	
	def tableview_number_of_rows(self, tv, section):
		sn = SECTIONS[section]
		return len(OPTIONS[sn])
	
	def tableview_cell_for_row(self, tv, section, row):
		sn = SECTIONS[section]
		info = OPTIONS[sn][row]
		otype = info["type"]
		if otype == TYPE_LABEL:
			cell = ui.TableViewCell("value1")
			cell.detail_text_label.text = str(info["value"])
		else:
			cell = ui.TableViewCell("default")
		cell.flex = ""
		if otype == TYPE_BOOL:
			switch = ui.Switch()
			switch.value = _stash.config.getboolean(
				sn, info["option_name"]
				)
			i = (sn, info["option_name"])
			callback = lambda s, self=self, i=i: self.switch_changed(s, i)
			switch.action = callback
			cell.content_view.add_subview(switch)
			switch.y = (cell.height / 2.0) - (switch.height / 2.0)
			switch.x = (cell.width - switch.width) - (cell.width / 20)
			switch.flex = "L"
		elif otype == TYPE_CHOICE:
			seg = ui.SegmentedControl()
			seg.segments = info["choices"]
			try:
				cur = _stash.config.get(sn, info["option_name"])
				curi = seg.segments.index(cur)
			except:
				curi = -1
			seg.selected_index = curi
			i = (sn, info["option_name"])
			callback = lambda s, self=self, i=i: self.choice_changed(s, i)
			seg.action = callback
			cell.content_view.add_subview(seg)
			seg.y = (cell.height / 2.0) - (seg.height / 2.0)
			seg.x = (cell.width - seg.width) - (cell.width / 20)
			seg.flex = "LW"
		elif otype == TYPE_COLOR:
			b = ui.Button()
			rawcolor = _stash.config.get(sn, info["option_name"])
			color = ast.literal_eval(rawcolor)
			rgb255color = color[0] * 255, color[1] * 255, color[2] * 255
			b.background_color = color
			b.title = "#%.02X%.02X%.02X" % rgb255color
			b.tint_color = ((0, 0, 0) if color[0] >= 0.5 else (1, 1, 1))
			i = (sn, info["option_name"])
			callback = lambda s, self=self, i=i: self.choose_color(s, i)
			b.action = callback
			cell.content_view.add_subview(b)
			b.width = (cell.width / 6.0)
			b.height = ((cell.height / 4.0) * 3.0)
			b.y = (cell.height / 2.0) - (b.height / 2.0)
			b.x = (cell.width - b.width) - (cell.width / 20)
			b.flex = "LW"
			b.border_color = "#000000"
			b.border_width = 1
		elif otype in (TYPE_STR, TYPE_INT):
			tf = ui.TextField()
			tf.alignment = ui.ALIGN_RIGHT
			tf.autocapitalization_type = ui.AUTOCAPITALIZE_NONE
			tf.autocorrection_type = False
			tf.clear_button_mode = "while_editing"
			tf.text = _stash.config.get(sn, info["option_name"])
			tf.delegate = self
			i = (sn, info["option_name"])
			callback = lambda s, self=self, i=i: self.str_entered(s, i)
			tf.action = callback
			if otype == TYPE_STR:
				tf.keyboard_type = ui.KEYBOARD_DEFAULT
			elif otype == TYPE_INT:
				tf.keyboard_type = ui.KEYBOARD_NUMBER_PAD
			tf.flex = "LW"
			cell.add_subview(tf)
			tf.width = (cell.width / 6.0)
			tf.height = ((cell.height / 4.0) * 3.0)
			tf.y = (cell.height / 2.0) - (tf.height / 2.0)
			tf.x = (cell.width - tf.width) - (cell.width / 20)
		elif otype == TYPE_FILE:
			# incomplete!
			b = ui.Button()
			fp = _stash.config.get(sn, info["option_name"])
			fn = fp.replace(os.path.dirname(fp), "", 1)
			b.title = fn
			i = (sn, info["option_name"])
			callback = lambda s, self=self, i=i, f=fp: self.choose_file(s, i, f)
			b.action = callback
			cell.content_view.add_subview(b)
			b.width = (cell.width / 6.0)
			b.height = ((cell.height / 4.0) * 3.0)
			b.y = (cell.height / 2.0) - (b.height / 2.0)
			b.x = (cell.width - b.width) - (cell.width / 20)
			b.flex = "LWH"
		elif otype == TYPE_COMMAND:
			b = ui.Button()
			b.title = info["display_name"]
			cmd = info["command"]
			if isinstance(cmd, (str, unicode)):
				f = lambda c=cmd: _stash(c, add_to_history=False)
			else:
				f = lambda c=cmd: cmd()
			callback = lambda s, self=self, f=f: self.run_func(f)
			b.action = callback
			cell.content_view.add_subview(b)
			b.flex = "WH"
			b.frame = cell.frame
			cell.remove_subview(cell.text_label)
		
		if otype != TYPE_COMMAND:
			title = info["display_name"]
		else:
			title = ""
		cell.text_label.text = title
		return cell
	
	def tableview_title_for_header(self, tv, section):
		return SECTIONS[section].capitalize()
	
	def tableview_can_delete(self, tv, section, row):
		return False
	
	def tableview_can_move(self, tv, section, row):
		return False
	
	def tableview_did_select(self, tv, section, row):
		# deselect row
		tv.selected_row = (-1, -1)
	
	def textfield_did_begin_editing(self, tf):
		self.cur_tf = tf
		self.hide_kb_button.enabled = True
	
	def keyboard_frame_did_change(self, frame):
		"""called when the keyboard appears/disappears."""
		h = frame[3]
		self.table.height = self.height - h
		if h == 0:
			self.hide_kb_button.enabled = False
		
	def save(self):
		"""saves the config."""
		with open(CONFIG_PATH, "w") as f:
			_stash.config.write(f)
	
	def hide_keyboard(self, sender):
		"""hides the keyboard."""
		if self.cur_tf is None:
			return
		self.cur_tf.end_editing()
		self.cur_tf = None
		self.hide_kb_button.enabled = False
	
	# callbacks
	
	@ui.in_background
	def switch_changed(self, switch, name):
		"""called when a switch was changed."""
		section, option = name
		v = ("1" if switch.value else "0")
		_stash.config.set(section, option, v)
		self.save()
	
	@ui.in_background
	def choice_changed(self, seg, name):
		"""called when a segmentedcontroll was changed."""
		section, option = name
		v = seg.segments[seg.selected_index]
		_stash.config.set(section, option, v)
		self.save()
	
	@ui.in_background
	def choose_color(self, b, name):
		"""called when the user wants to change a color."""
		section, option = name
		cur = b.background_color[:3]
		picker = ColorPicker(cur)
		self.subview_open = True
		rgb = picker.get_color()
		self.subview_open = False
		_stash.config.set(section, option, str(rgb))
		self.table.reload_data()
		self.save()
	
	@ui.in_background
	def str_entered(self, tf, name):
		"""called when a textfield ended editing."""
		section, option = name
		text = tf.text
		_stash.config.set(section, option, text)
		self.save()
	
	@ui.in_background
	def run_func(self, f):
		"""run a function while showing an ActivityIndicator()"""
		self.ai.start()
		try:
			f()
		finally:
			self.ai.stop()
	

if __name__ == "__main__":
	# main code
	cfg_view = ConfigView()
	cfg_view.show()
