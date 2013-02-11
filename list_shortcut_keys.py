#coding: utf8
#################################### IMPORTS ###################################

# Std Libs
import re

# Sublime Libs
import sublime

from .quick_panel_cols import format_for_display
from .jsonix import dumps as dumpsj

from .commands_base import EditJSONPreferenceBase

############################### BINDINGS DISPLAY ###############################

def format_binding_command(b):
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
    # TODO:  things like backquote and `
    return normalize_tabtriggers(normalize_modifier_sequencing(key))

def destructure_bindings(bindings):
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

class ListShortcutKeys(EditJSONPreferenceBase):
    format_cols   = (3, 4, 0, )
    extra_rows    = (-2, )
    platform      = sublime.platform().title()
    if platform   == 'Osx': platform = 'OSX'
    settings_pattern  = 'Default( \(%s\))?.sublime-keymap$' % platform

    def on_settings_json(self, pkg, name, f, text, settings_json, completions):
        for keys, command, cargs, scope in destructure_bindings(settings_json):
            if command == 'insert_binding_repr': continue
            
            nkey = normalize_binding_display(keys)

            completions.update([pkg, command])
            completions.update(re.findall(r'\w+', nkey))

            yield (pkg, f, keys, nkey, command, cargs, scope)

    def on_selection(self, setting):
        f, keys, nkey, command, cargs, scope = setting[1:]
        regions = [[keys[0].__inner__()[0],  keys[-1].__inner__()[1]]]
        return f, None, regions