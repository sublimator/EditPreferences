#coding: utf8
#################################### IMPORTS ###################################

# Sublime Libs
import sublime_plugin

from .quick_panel_cols import format_for_display
from .helpers import glob_packages, temporary_event_handler, \
                     package_file_contents, normalise_to_open_file_path
from .jsonix import decode_with_ix, strip_json_comments, loads as loadsj

def glob_and_parse_package_json(pattern):
    for pkg, name, f in glob_packages(pattern):
        text = package_file_contents(f)
        text = strip_json_comments(text)
        if not text: continue

        with decode_with_ix():
            setting_dict = loadsj(text)

        yield pkg, name, f, text, setting_dict

class IEditJSONPreference:
    "Just factored out all overideables into this class for visibility"
    format_cols = () # MUST_IMPLEMENT
    extra_rows = ()
    settings_pattern = "*.sublime-json" # MUST OVERRIDE

    def on_settings_json(self, pkg, name, f, text, setting_dict, completions):
        "must implement"
    def on_selection(self, setting):
        "must implement"
    def format_for_display(self, settings):
        return settings # for quick panel

class EditJSONPreferenceBase(sublime_plugin.WindowCommand, IEditJSONPreference):
    def format_for_display(self, rows):
        display = format_for_display(rows, cols=self.format_cols)
        
        if self.extra_rows:
            display =  list(map(list, zip(display, *[[m[i] for m in rows]
                                                    for i in self.extra_rows])))
        return  display

    def run(self):
        window      = self.window
        settings    = []
        completions = set()

        for pkg, name, f, text, setting_dict in \
                    glob_and_parse_package_json(self.settings_pattern):

            settings.extend(self.on_settings_json (
                    pkg, name, f, text, setting_dict, completions))

        display = self.format_for_display(settings)
        ch = temporary_event_handler( lambda *a: [(c,c) for c in completions],
                                      'on_query_completions')

        def on_select(i, on_highlight=False):
            if not on_highlight:
                ch.remove()

            if i != -1:
                fn, lineno, regions = self.on_selection(settings[i])
                fn = normalise_to_open_file_path(fn)
                window.run_command("open_file_enhanced", {"file" :  (fn),
                                                          "regions" : regions})

        on_highlight=lambda i: i
        window.show_quick_panel(display, on_select,
                                         on_highlight=on_highlight,
                                         flags=1)