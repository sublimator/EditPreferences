#coding: utf8
#################################### IMPORTS ###################################

# Std Libs
import itertools
import string
import json

# Sublime Libs
import sublime
import sublime_plugin

################################### CONSTANTS ##################################

MODS   = ['super', 'ctrl', 'alt', 'shift']
COMBOS = ['alt',
          'alt+shift',
          'ctrl',
          'ctrl+alt',
          'ctrl+alt+shift',
          'ctrl+shift',
          'super',
          'super+alt',
          'super+alt+shift',
          'super+ctrl',
          'super+ctrl+alt',
          'super+ctrl+alt+shift',
          'super+ctrl+shift',
          'super+shift']

# combs = set()
# for i in range(1, len(MODS)+1):
#     for comb in itertools.combinations(MODS, i):
#         combs.add('+'.join(comb))
# combs.remove('shift')
# import pprint
# pprint.pprint(combs)

################################################################################

class InsertBindingRepr(sublime_plugin.TextCommand):
    def run(self, edit, val=''):
        v    = self.view
        s    = v.settings()
        k    = 'insert_binding_repr_expecting'

        mods = s.get(k)

        if mods:
            s.set(k, None) # the modifiers
            s.set('expecting_binding_repr_mode', False)
            #  insert the repr
            v.run_command('insert', dict(characters= mods+'+'+val))
        else:
            s.set(k, val) # the modifiers
            s.set('expecting_binding_repr_mode', True)

def do():
    def get_shift(xxx_todo_changeme):
         (c, c2) = xxx_todo_changeme
         return abs(ord(c) - ord(c2))
    
    print(list(map(get_shift, [('1', '!'), ('4', '$')])))

def create_keys():
    bindings = [{
        'keys': [c + '+='],
        'command': 'insert_binding_repr',
        'args': {'val': c},
        'context': [
          {"key": "overlay_visible", "operator": "equal", "operand": True },
          {"key": "setting.expecting_binding_repr_mode", "operand": False, "operator": "equal"} 
        ]

    } for c in COMBOS]

    def bt(): return {
        'keys': [],
        'command' : 'insert_binding_repr',
        'args': {'val': None},
        'context': [
          { "key": "overlay_visible", "operator": "equal", "operand": True },
          {"key": "setting.expecting_binding_repr_mode", "operand": True, "operator": "equal"} 
        ]
    }

    BINDINGS=(
        ('pageup,pagedown,home,end,insert,delete,backspace,tab,'
         'escape,pause,up,down,left,right,') 
         + ','.join('f'+str(i) for i in range(1,16)) )

    for k in list(string.printable[:-5]) + BINDINGS.split(','):
        bindings.append(bt())
        binding = bindings[-1]

        binding['keys'].append(k)
        binding['args']['val'] = k

    bindings = json.dumps(bindings)
    sublime.set_clipboard(bindings[1:-1]) # remove the surround `[` and `]`
    return bindings

def mod_combos():
    combos = []

    for n in range(1, 4):
        combos.extend(list(itertools.combinations(MODS, n)))
    
    ['+'.join(c) for c in combos if c != ('shift', )]

def printables():
    for ch in string.printable[:-5]:
        print(repr(ch))

################################################################################