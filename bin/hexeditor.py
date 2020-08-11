```Very Simple Hex Editor
```
import os
import clipboard

from dialogs import input_alert, hud_alert, form_dialog
from math import floor, ceil
from ui import *


class TfDelegate1:
	def textfield_did_end_editing(self, textfield):
		if textfield.text == 'POP':
			textfield.superview.superview.dump.pop()
			textfield.superview.superview.shift_offset(textfield.superview.superview.prev_offset)
		elif textfield.text == 'ADD':
			d = textfield.superview.superview.dump
			d.append('{}:    00 00 00 00 00 00 00 00    |........|'.format(hex(len(d)*8)[2:].zfill(7)))
			textfield.superview.superview.shift_offset(textfield.superview.superview.prev_offset)
		else:
			col = floor(int(textfield.text, 16)/8)
			textfield.superview.superview.shift_offset(col)
class TfDelegate2:
	def textfield_did_end_editing(self, textfield):
		textfield.superview.superview.alter_hex(textfield.text)
class TfDelegate3:
	def textfield_did_end_editing(self, textfield):
		textfield.superview.superview.alter_by_ascii(textfield.text)

class Display(View):
	def create_dump(self, sender):
		txt = []
		with open(input_alert('Make a hex dump of which file?'), 'rb') as f:
			while True:
				line = f.readline()
				if not line: break
				for byte in line:
					txt.append(byte)
		dump = []
		offset = 1
		while True:
			line = list(txt[offset-1:offset+7])
			if not line: break
			hexes = [hex(num)[2:].zfill(2) for num in line]
			for i in range(0, len(line)):
				if not line[i] in range(32, 127):
					line[i] = 46
			ascii_text = ''.join([chr(ch) for ch in line])
			offset_string = hex(offset-1)[2:].zfill(7)
			hex_string = ' '.join(hexes)
			dump.append(('{}:    {}{}|{}{}|'.format(offset_string, hex_string, ' '*(27-len(hex_string)), ascii_text, ' '*(8-len(ascii_text)))))
			offset += 8
		self.dump = dump
		self['textview1'].text = '\n'.join(dump)
		self['offset'].text = '0000000'
		self['hexstring'].text = dump[0][12:35]
		self['asciistring'].text = dump[0][40:48]
	
	def restore(self, sender):
		txt = '\n'.join(self.dump)
		arr = []
		for line in txt.split('\n'):
			hex_string = line[12:35]
			for byte in hex_string.split(' '):
				if byte:
					arr.append(int(byte, 16))
		with open(input_alert('New file name?'), 'wb') as f:
			f.write(bytes(arr))
		hud_alert('Restoration complete!', 'success')
	
	def load_dump(self, sender):
		with open(input_alert('Load which hex dump?'), 'r') as f:
			self.dump = f.read().split('\n')
		self.dump.pop()
		self['textview1'].text = '\n'.join(self.dump)
		self['offset'].text = '0000000'
		self['hexstring'].text = self.dump[0][12:35]
		self['asciistring'].text = self.dump[0][40:48]
	
	def copy_dump(self, sender):
		clipboard.set('\n'.join(self.dump))
		hud_alert('Copy Succesful', 'success')
	
	def shift_offset(self, new_offset):
		self.prev_offset = new_offset
		try:
			line = self.dump[new_offset]
		except IndexError:
			line = self.dump[new_offset-1]
		self['offset'].text = line[1:7]
		self['hexstring'].text = line[12:35]
		self['asciistring'].text = line[40:48]
		self['textview1'].text = '\n'.join(self.dump)
	
	def alter_hex(self, new_hexstring):
		new_hexstring = new_hexstring[0:23]
		offset = floor(int(self['offset'].text, 16)/8)
		hexstring = [ch.zfill(2) for ch in new_hexstring.split(' ')]
		asciistring = ''
		for ch in hexstring:
			ch = int(ch, 16)
			if ch in range(32, 127): asciistring += chr(ch)
			else: asciistring += '.'
		new_line = '{}:    {}{}|{}{}|'.format(hex(offset*8)[2:].zfill(7), ' '.join(hexstring), ' '*(27-len(' '.join(hexstring))), asciistring, ' '*(8-len(asciistring)))
		self.dump[offset] = new_line
		self['offset'].text = hex(offset*8)[2:].zfill(7)
		self['hexstring'].text = ' '.join(hexstring)
		self['asciistring'].text = asciistring
		self['textview1'].text = '\n'.join(self.dump)
	
	def alter_by_ascii(self, ascii):
		ascii = ascii[0:8]
		hexstring = ' '.join([hex(ord(ch))[2:] for ch in ascii])
		self.alter_hex(hexstring)
	
	def change_settings(self, sender):
		bg_hex = self.background_color[0:3]
		bg_hex = '#' + ''.join([hex(ceil(num*255))[2:].zfill(2) for num in bg_hex])
		tc_hex = self['textview1'].text_color[0:3]
		tc_hex = '#' + ''.join([hex(ceil(num*255))[2:].zfill(2) for num in tc_hex])
		new_sets = form_dialog(title='Settings', fields=[{'type': 'text', 'title': 'Background Color', 'autocapitalization': AUTOCAPITALIZE_ALL, 'value': bg_hex}, {'type': 'text', 'title': 'Text Color', 'autocapitalization': AUTOCAPITALIZE_ALL, 'value': tc_hex}])
		if new_sets:
			self.background_color = new_sets['Background Color']
			self['textview1'].text_color = new_sets['Text Color']
			with open('.settings', 'w') as f:
				f.write(new_sets['Background Color'] + '\n' + new_sets['Text Color'])
	
	def __init__(self):
		View.__init__(self)
		self.dump = []
		self.prev_offset = 0
		if not os.path.exists('.settings'):
			with open('.settings', 'w') as f:
				f.write('#ffffff\n#000000')
	
	def __getitem__(self, key):
		return self.subviews[0][key]
	
	def did_load(self):
		settings = ''
		with open('.settings', 'r') as f:
			settings = f.read().strip().split('\n')
		self.background_color = settings[0]
		self['textview1'].text_color = settings[1]
		self.old_frames = {}
		for key in ['offset', 'hexstring', 'asciistring']:
			self.old_frames.update({key: self[key].frame})
		add = ButtonItem()
		add.image = Image.named('iob:ios7_plus_empty_32')
		add.action = self.create_dump
		clip = ButtonItem()
		clip.image = Image.named('iob:ios7_copy_outline_32')
		clip.action = self.copy_dump
		rest = ButtonItem()
		rest.image = Image.named('iob:disc_24')
		rest.action = self.restore
		load = ButtonItem()
		load.image = Image.named('iob:ios7_download_outline_32')
		load.action = self.load_dump
		settings = ButtonItem()
		settings.image = Image('iob:gear_a_24')
		settings.action = self.change_settings
		self.right_button_items = [add, clip, settings]
		self.left_button_items = [rest, load]
		self['textview1'].editable = False
		self['offset'].delegate = TfDelegate1()
		self['hexstring'].delegate = TfDelegate2()
		self['asciistring'].delegate = TfDelegate3()
	
	def keyboard_frame_did_change(self, frame):
		for key in ['offset', 'hexstring', 'asciistring']:
			ox, oy, ow, oh = self[key].frame
			kx, ky, kw, kh = convert_rect(frame, self)
			if not frame == (0.00, 0.00, 0.00, 0.00):
				new_frame = (ox, ky-(4*oh)-10, ow, oh)
				self[key].frame = new_frame
			else:
				self[key].frame = self.old_frames[key]


load_view('hexeditor').present(orientations=['landscape'])
