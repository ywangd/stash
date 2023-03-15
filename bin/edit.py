# -*- coding: utf-8 -*-
"""
Used to create/open and edit files.
[-t --temp] - Opens the file as a temporary file. Allowing editing and renaming. Previous script in the pythonista editor will be restored unless a new tab is edited.
[-o --old_tab] - Open file in an old editor tab (default is new tab, which is possible from Pythonista 1.6, although not for make_new_file; see https://forum.omz-software.com/topic/2428/editor-observations)

usage:
    edit [-t --temp] [-o --old_tab] [file]
    Follow prompt for instructions.
"""
from __future__ import print_function
import os
import tempfile
import console
import editor
import time
import argparse

_stash = globals()["_stash"]

try:
    raw_input
except NameError:
    raw_input = input


def open_temp(file='', new_tab=True):
    try:
        file_to_edit = file
        temp = tempfile.NamedTemporaryFile(dir=os.path.expanduser('~/Documents'), suffix='.py')
        cur_path = editor.get_path()
        if file_to_edit != '':
            try:
                to_edit = open(file_to_edit, 'r')
            except:
                to_edit = open(file_to_edit, 'w+')

            temp.write(to_edit.read())
            temp.flush()
            to_edit.close()

        print('***When you are finished editing the file, you must come back to console to confim changes***')
        editor.open_file(temp.name, new_tab)
        time.sleep(1.5)
        console.hide_output()
        input = raw_input('Save Changes? Y,N: ')

        if input == 'Y' or input == 'y':
            while True:
                try:
                    save_as = raw_input('Save file as [Enter to confirm]: %s' % file_to_edit) or file_to_edit
                except:
                    save_as = file_to_edit
                if save_as:
                    break

            if not new_tab:
                editor.open_file(cur_path)  # restore previous script in editor
            with open(save_as, 'w') as f:
                with open(temp.name, 'r') as tmp:
                    f.write(tmp.read())

            print('File Saved.')
        elif input == 'N' or input == 'n':
            if not new_tab:
                editor.open_file(cur_path)  # restore previous script in editor

    except Exception as e:
        print(e)

    finally:
        temp.close()


def open_editor(file='', new_tab=True):
    if os.path.isfile(os.getcwd() + '/' + file):
        editor.open_file(os.getcwd() + '/' + file, new_tab)
        console.hide_output()
    else:
        editor.make_new_file(file if file else 'untitled.py')  # new_tab not supported by make_new_file


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('-t', '--temp', action='store_true', default=False, help='open file to a temp file')
    ap.add_argument(
        '-o',
        '--old_tab',
        action='store_true',
        default=False,
        help='open file in an old editor tab (default is new tab)'
    )
    ap.add_argument('file', action='store', nargs='?', default=False, help='File to open')
    ns = ap.parse_args()

    # Calculate the relative path because absolute path crashes Pythonista
    # most likely due to access right for iOS root path.
    if ns.file:
        filename = os.path.expanduser(ns.file)
        filename = os.path.relpath(filename, '.')

    if ns.temp and ns.file:
        open_temp(filename, new_tab=not ns.old_tab)

    elif ns.file:
        open_editor(filename, new_tab=not ns.old_tab)

    else:
        open_temp(new_tab=not ns.old_tab)
