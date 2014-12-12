'''
Used to create/open and edit files.
    
usage:
    edit <file>
    Follow prompt for instructions.
'''
import os
import sys
import console
import editor
import time

TEMP_NAME = '.edit_temp.py'

temp_edit_path = os.path.relpath(os.path.realpath(os.path.dirname(__file__)),os.path.expanduser('~/Documents'))+'/'+TEMP_NAME
temp_edit_dir = os.path.abspath(os.path.dirname(__file__))
file_to_edit = sys.argv[1]
cur_path = editor.get_path()

try:
    file = open(temp_edit_dir+'/'+TEMP_NAME,'w')
    try:
        to_edit = open(file_to_edit,'r')
    except:
        to_edit = open(file_to_edit,'w+')
        
    file.write(to_edit.read())
    to_edit.close()
    file.close()
    editor.reload_files()
    print '***When you are finished editing the file, you must come back to console to confim changes***'
    editor.open_file(temp_edit_path)
    time.sleep(2)
    console.hide_output()
    input = raw_input('Save Changes? Y,N: ')

    if input=='Y' or input=='y':
        try:
            save_as = raw_input('Save file as [Enter to confirm]: %s' % file_to_edit) or file_to_edit
        except:
            save_as = file_to_edit
        editor.open_file(cur_path)
        tmp = open(temp_edit_dir+'/'+TEMP_NAME,'r')
        cur = open(save_as,'w')
        cur.write(tmp.read())
        cur.close()
        tmp.close()
        os.remove(temp_edit_dir+'/'+TEMP_NAME)

    elif input=='N' or input=='n':
        editor.open_file(cur_path)
        os.remove(temp_edit_dir+'/'+TEMP_NAME)



except Exception, e:
    print e

