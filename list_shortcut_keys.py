#coding: utf8
#################################### IMPORTS ###################################

# Std Libs
import re

# Sublime Libs
import sublime_plugin
import sublime

from .quick_panel_cols import format_for_display
from .helpers import glob_packages, temporary_event_handler, \
                     package_file_contents, \
                     normalise_to_open_file_path

# from .jsonix import strip_json_comments
from .jsonix import decode_with_ix, strip_json_comments, loads as loadsj, \
                    dumps as dumpsj

############################### BINDINGS DISPLAY ###############################

def format_binding_command(b):
    # fmt = '%s: %s'
     # '.join(fmt % a for a in b['args'].items())
    return b['command']

def normalize_tabtriggers(key):
    if key.endswith(',tab'):
        key = ''.join(key[:-4].split(',')) + '<tab>'

    return key

def normalize_modifier_sequencing(keys):
    rebuilt_key = []

    for combo in keys:
        keys          = combo.split('+')
        rebuilt_combo = []

        for mod in ('super', 'ctrl', 'alt', 'shift'):
            if mod in keys:
                rebuilt_combo.append(keys.pop(keys.index(mod)))

        rebuilt_combo.extend(keys)
        rebuilt_key.append('+'.join(rebuilt_combo))

    return ','.join(rebuilt_key)

def normalize_binding_display(key):
    return normalize_tabtriggers(normalize_modifier_sequencing(key))

def parse_keymap(f):
    text = package_file_contents(f)
    text = strip_json_comments(text)
    with decode_with_ix():
        bindings = loadsj(text)

    for binding in bindings:
        keys     = binding.get('keys')
        args     = dumpsj(binding.get('args', {}))

        command = format_binding_command(binding)
        scope   = [ c for c in  binding.get('context', []) if
                    c.get('key') =="selector" ]
        if scope:
            scope = scope[0]['operand']
        else:
            scope = 'source,plain'

        yield keys, command, args, scope

################################################################################

class ListShortcutKeysCommand(sublime_plugin.WindowCommand):
    instance = None

    def run(self, args=[]):
        window      = self.window

        args        = []
        platform    = sublime.platform().title()
        if platform == 'Osx': platform = 'OSX'

        keymap      = 'Default( \(%s\))?.sublime-keymap$' % platform
        keymaps     = glob_packages(keymap)
        completions = set()

        for pkg, name, f in keymaps:
            try:
                for i, (keys, command, cargs, scope), in enumerate(parse_keymap(f)):
                    nkey = normalize_binding_display(keys)

                    args.append( (pkg, f, keys, nkey, command, i, cargs, scope) )
                    completions.update([pkg, command])
                    completions.update(re.findall(r'\w+', nkey))
                    # completions.add(pkg)

            except Exception as e:
                print("Error parsing keymap, look for trailing commas and /* style */ comments")
                print(e, f)


        def oqc(*args):
            return list([(c,c) for c in completions])

        ch = temporary_event_handler(oqc, 'on_query_completions')

        def on_select(i):
            ch.remove()

            if i != -1:
                f, keys, nkey, command, nth, cargs, scope = args[i][1:]


                fn = normalise_to_open_file_path(f)
                regions = [
                    [
                        keys[0].__inner__()[0],
                        keys[-1].__inner__()[1],
                    ]
                ]
                window.run_command("open_file_enhanced", {"file" :  (fn),
                                                          "regions" : regions})

        display = format_for_display(args, cols = (3, 0, 4))
        display = list(map(list, list(zip(display, [a[-2] for a in args]))))
        window.show_quick_panel(display, on_select, 1)