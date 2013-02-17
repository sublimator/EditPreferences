
#coding: utf8
#################################### IMPORTS ###################################

# Std Libs
import os
from os.path import splitext

# Sublime Libs
import sublime_plugin
import sublime

from .quick_panel_cols import format_for_display

from .package_resources import glob_packages, package_file_exists,\
                               norm_path_to_sublime_style, platform_specifier

################################### CONSTANTS ##################################

SUBLIME_KEYMAP = "[]"
CREATE_FILES_FOR = ('sublime-keymap', 'sublime-settings')

################################################################################

def open_preference_optionally_creating(f, window):
    if not package_file_exists(f):
        if f.endswith('sublime-keymap'):
            to_write = SUBLIME_KEYMAP

        elif f.endswith('sublime-settings'):
            to_write = '{}'
        else:
            to_write = None

        # Safeguard FFFFK
        if '.sublime-package/' in f:
            print ("Todo, '.sublime-package/' in f:, "
                   "while trying to create preference file ")
            to_write = False

        if splitext(f)[1][1:] in CREATE_FILES_FOR and to_write:
            with open(f, 'w') as fh:
                fh.write(to_write)

    fn    = norm_path_to_sublime_style(f)
    window.run_command("open_file_enhanced", {"file" :  (fn)})

class EditPackageFiles(sublime_plugin.WindowCommand):
    def run(self, pref_type =None):
        window    = self.window
        files     = list(glob_packages(pref_type))
        keymap    = 'Default (%s)' % platform_specifier()

        if pref_type == 'sublime-keymap':
            display = [(
                (' + ' if not package_file_exists(f[2]) else ' '),
                f[0],
                f[1] if f[1] != keymap else ' ')
                for f in files ]
        else:
            display = [
                ((' + ' if not package_file_exists(f[2]) else ' '),

                f[0],
                f[1] if f[0] != f[1] else ' ')
                for f in files ]

        # Kill that first column yo
        if all(r[0] == ' ' for r in display):
            display = [r[1:] for r in display]

        display = format_for_display(display)

        sublime.status_message  (
            'Please choose %s file to %s' % (pref_type, 'edit'))

        def on_select(i):
            if i != -1:
                f = files[i][2]
                open_preference_optionally_creating(f, window)

        window.show_quick_panel(display, on_select, 1)