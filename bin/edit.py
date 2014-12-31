'''
Used to create/open and edit files.
    
usage:
    edit <file>
    Follow prompt for instructions.
'''
import os
import tempfile
import console
import editor
import time

try:
    file_to_edit = sys.argv[1]
    temp = tempfile.NamedTemporaryFile(dir=os.path.expanduser('~/Documents') , suffix='.py')
    cur_path = editor.get_path()
    #file = open(temp_edit_dir+'/'+TEMP_NAME,'w')
    try:
        to_edit = open(file_to_edit,'r')
    except:
        to_edit = open(file_to_edit,'w+')
        
    temp.write(to_edit.read())
    #temp.seek(0)
    temp.flush()
    to_edit.close()
    print '***When you are finished editing the file, you must come back to console to confim changes***'
    editor.open_file(temp.name)
    time.sleep(1.5)
    console.hide_output()
    input = raw_input('Save Changes? Y,N: ')

    if input=='Y' or input=='y':
        try:
            save_as = raw_input('Save file as [Enter to confirm]: %s' % file_to_edit) or file_to_edit
        except:
            save_as = file_to_edit
        
        editor.open_file(cur_path)
        with open(save_as,'w') as f:
            with open(temp.name,'r') as tmp:
                f.write(tmp.read())
                
        print 'File Saved.'
    elif input=='N' or input=='n':
        editor.open_file(cur_path)

except Exception, e:
    print e
    
finally:
    temp.close()

