#coding: utf8
#################################### IMPORTS ###################################

# Std Libs
import re
from pprint import pprint

# Sublime Libs
import sublime_plugin

from .quick_panel_cols import format_for_display
from .helpers import glob_packages, temporary_event_handler, \
                     package_file_contents, \
                     normalise_to_open_file_path

from .jsonix import decode_with_ix, strip_json_comments, loads as loadsj, \
                    dumps as dumpsj

class ListMenuBindings(sublime_plugin.WindowCommand):
    def run(self, file_type='sublime-menu'):
        completions = set()
        menus       = []
        display     = []
        window      = self.window

        with decode_with_ix():
            for pkg, name, f in glob_packages(file_type):
                pkg_display = "%s - %s" % (pkg, name) if name != pkg else pkg

                text = package_file_contents(f)
                text = strip_json_comments(text)
                if not text: continue

                completions.update(re.findall(r'\w+', text))
                try:
                    menu = loadsj(text)
                except:
                    print(f, repr(text))
                    raise

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

        display = format_for_display(menus, cols=(1,3))
        display = list(map(list, list(zip(display, *[[m[i] for m in menus]
                                            for i in (-2, -1 )]))))
        ch = temporary_event_handler(
            lambda *a: list((c,c) for c in completions),
            'on_query_completions')

        def on_select(i):
            ch.remove()

            if i != -1:
                ident = menus[i][-2]
                fn = menus[i][0]
                fn    = normalise_to_open_file_path(fn)

                try:    regions = [list(ident.__inner__())]
                except: regions = [list(ident.__outer__())]

                window.run_command("open_file_enhanced", {"file" :  (fn),
                                                          "regions" : regions})

        window.show_quick_panel(display, on_select, 1)