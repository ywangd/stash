# coding: utf-8
'''
Manipulate action (wrench) menu
example:
     add_action('/stash/launch_stash.py','monitor')
     save_defaults() # so it is stored for next launch

 '''

# This module was created by jsbain. Thanks for sharing it!

from builtins import str
from objc_util import *
NSUserDefaults = ObjCClass('NSUserDefaults')


def add_action(scriptName, iconName='python', iconColor='', title=''):
	'''adds an editor action.  scriptName should start with /
	(e.g /stash/stash.py)
	iconName should be an icon without leading prefix,
	or trailing size.  i.e alert instead of iob:alert_256
	iconColor should be a web style hex string, eg aa00ff
	title is the alternative title
	Call save_defaults() to store defaults
	')'''
	defaults = NSUserDefaults.standardUserDefaults()
	kwargs = locals()
	entry = {
		key: kwargs[key] for key in (
			'scriptName', 'iconName', 'iconColor', 'title', 'arguments'
			)
		if key in kwargs and kwargs[key]
		}
	editoractions = get_actions()
	editoractions.append(ns(entry))
	defaults.setObject_forKey_(editoractions, 'EditorActionInfos')

		
def remove_action(scriptName):
	''' remove all instances of a given scriptname.
	Call save_defaults() to store for next session
	'''
	defaults = NSUserDefaults.standardUserDefaults()
	editoractions = get_actions()
	[
		editoractions.remove(x) for x in editoractions
		if str(x['scriptName']) == scriptName
		]
	defaults.setObject_forKey_(editoractions, 'EditorActionInfos')

		
def remove_action_at_index(index):
	''' remove action at index.  Call save_defaults() to save result.
	'''
	defaults = NSUserDefaults.standardUserDefaults()
	editoractions = get_actions()
	del editoractions[index]
	defaults.setObject_forKey_(editoractions, 'EditorActionInfos')

	
def get_defaults_dict():
	'''return NSdictionary of defaults'''
	defaults = NSUserDefaults.standardUserDefaults()
	return defaults.dictionaryRepresentation()

		
def get_actions():
	'''return action list'''
	defaults = NSUserDefaults.standardUserDefaults()
	return list(defaults.arrayForKey_('EditorActionInfos'))

		
def save_defaults():
	'''save current set of defaults'''
	defaults = NSUserDefaults.standardUserDefaults()
	NSUserDefaults.setStandardUserDefaults_(defaults)
