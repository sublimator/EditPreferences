#coding: utf8
#################################### IMPORTS ###################################

# Std Libs
import re
from pprint import pprint

# Sublime Libs

from .quick_panel_cols import format_for_display
from .jsonix import dumps as dumpsj
from .commands_base import EditJSONPreferenceBase

class ListMenuBindings(EditJSONPreferenceBase):
    format_cols = (1,3)
    extra_rows = (-2, -1, )
    settings_pattern = "sublime-menu"

    def on_settings_json(self, pkg, name, f, text, menu, completions):
        pkg_display = "%s - %s" % (pkg, name) if name != pkg else pkg
        completions.update(re.findall(r'\w+', text))

        menus = []
        def walk(menu, parent=''):
            for item in menu:
                if item.get('children'):
                    walk(item['children'],
                        parent=item.get('caption', ''))
                else:
                    try:
                        row1 = item.get('caption') or item.get('command')
                        row2 = dumpsj (item.get('args', {}))
                        cmd = item.get('command') or ''
                    except Exception as e:
                        pprint(locals())
                        print(e)
                        raise

                    menus.append (
                        (f,
                            pkg_display + ((' - %s' % parent)
                                             if parent else '' ),
                            parent,
                            row1,
                            cmd,
                            row2, ) )
        walk(menu)
        return menus

    def on_selection(self, setting):
        ident = setting[-2]
        fn = setting[0]

        try:    regions = [list(ident.__inner__())]
        except: regions = [list(ident.__outer__())]

        return fn, None, regions
