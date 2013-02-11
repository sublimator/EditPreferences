#coding: utf8
#################################### IMPORTS ###################################

# Std Libs
import re
from pprint import pprint

# Sublime Libs
from .quick_panel_cols import format_for_display
from .jsonix import dumps as dumpsj
from .commands_base import EditJSONPreferenceBase

class ListThemeSelectors(EditJSONPreferenceBase):
    format_cols = (1, 2)
    extra_rows = (-1, )
    settings_pattern = "sublime-theme"

    def on_settings_json(self, pkg, name, f, text, selectors, completions):
        pkg_display = "%s - %s" % (pkg, name) if name != pkg else pkg
        completions.update(re.findall(r'\w+', text))

        for selector in selectors:
            # Popping these badboys from dict so do they aren't just noise in
            # the `extra_rows`
            class_ = selector.pop('class', None)
            attributes = selector.pop('attributes', '')

            if attributes:
                attributes = "[%s]" %  ', '.join(['@'+a for a in attributes])
            css_fmt =  ".%s%s" % (class_, attributes) 
            yield (f, css_fmt, pkg_display, class_, dumpsj(selector))

    def on_selection(self, setting):
        fn = setting[0]
        class_ = setting[-2]

        try:    regions = [list(class_.__inner__())]
        except: regions = [list(class_.__outer__())]

        return fn, None, regions
