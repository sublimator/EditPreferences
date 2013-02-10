#coding: utf8
#################################### IMPORTS ###################################

# Std Libs
import re

from .jsonix import dumps as dumpsj
from .commands_base import EditJSONPreferenceBase

class ListSettings(EditJSONPreferenceBase):
    format_cols = (2,3,1)
    settings_pattern = 'sublime-settings'

    def on_settings_json(self, pkg, name, f, text, setting_dict, completions):
        pkg_display = "%s - %s" % (pkg, name) if name != pkg else pkg
        completions.update(re.findall(r'\w+', text))

        for setting, value in list(setting_dict.items()):
            yield (f, pkg_display, setting, dumpsj(value), value)

    def on_selection(self, setting):
        key    = setting[2]
        value  = setting[-1]
        fn     = setting[0]
        lineno = None

        try:    regions = [list(value.__inner__())]
        except: regions = [list(key.__inner__())]

        return fn, lineno, regions