#coding: utf8
#################################### IMPORTS ###################################

# Std Libs
import re
# import functools

# Sublime Libs
import sublime_plugin

from .quick_panel_cols import format_for_display
from .helpers import glob_packages, temporary_event_handler, \
                     package_file_contents, normalise_to_open_file_path
from .jsonix import decode_with_ix, strip_json_comments, loads as loadsj, \
                    dumps as dumpsj

class ListSettings(sublime_plugin.WindowCommand):
    def run(self, args=[]):
        window      = self.window
        settings    = []
        completions = set()

        with decode_with_ix():
            for pkg, name, f in glob_packages('sublime-settings'):

                pkg_display = "%s - %s" % (pkg, name) if name != pkg else pkg
                text = package_file_contents(f)
                text = strip_json_comments(text)
                if not text: continue

                completions.update(re.findall(r'\w+', text))
                try:
                    setting_dict = loadsj(text)
                except:
                    # print((f, repr(text)))
                    raise

                for setting, value in list(setting_dict.items()):
                    settings.append (
                        (f, pkg_display, setting, dumpsj(value), value))
        
        display = format_for_display(settings, cols=(2,3,1))
        ch = temporary_event_handler( lambda *a: [(c,c) for c in completions],
                                      'on_query_completions')
        
        def on_select(i, on_highlight=False):
            if not on_highlight:
                ch.remove()

            if i != -1:
                key   = settings[i][2]
                value = settings[i][-1]
                fn    = settings[i][0]
                fn    = normalise_to_open_file_path(fn)
                
                try:    regions = [list(value.__inner__())]
                except: regions = [list(key.__inner__())]

                window.run_command("open_file_enhanced", {"file" :  (fn), 
                                                          "regions" : regions})

        on_highlight=lambda i: i
        # on_highlight=functools.partial(on_select, on_highlight=1)
        window.show_quick_panel(display, on_select, 
                                         on_highlight=on_highlight, 
                                         flags=1)