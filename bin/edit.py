'''
Used to create/open and edit files.
[-t --temp] - Opens the file as a temporary file. Allowing editing and renaming. Previous script in the pythonista editor will be restored.
    
usage:
    edit [-t --temp] [file]
    Follow prompt for instructions.
'''
import os
import tempfile
import console
import editor
import time
import argparse

ap = argparse.ArgumentParser()
ap.add_argument('-t','--temp',action='store_true',default=False,help='Open file to a temp file.')
ap.add_argument('file', action='store',nargs='?',default=False,help='File to open')
args = ap.parse_args()

def open_temp(file=''):
    try:
        file_to_edit = file
        temp = tempfile.NamedTemporaryFile(dir=os.path.expanduser('~/Documents') , suffix='.py')
        cur_path = editor.get_path()
        if file_to_edit != '':
            try:
                to_edit = open(file_to_edit,'r')
            except:
                to_edit = open(file_to_edit,'w+')

            temp.write(to_edit.read())
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
    
def open_editor(file=''):
    if os.path.isfile(os.getcwd()+'/'+file):
        editor.open_file(os.getcwd()+'/'+file)
        console.hide_output()
    else:
        print 'File not found.'
        
if __name__=='__main__':
    if args.temp and args.file:
        print args.file
        open_temp(args.file)
    elif args.file:
        open_editor(args.file)
    else:
        open_temp()




