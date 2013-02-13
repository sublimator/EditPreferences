#coding: utf8
#################################### IMPORTS ###################################

# Std Libs
import functools
import textwrap

# Sublime Libs
import sublime
import sublime_plugin

################################### CONSTANTS ##################################

class Delay(int): pass
class Pause: pass
class Callback: pass
class AwaitCallback: pass
class Cancel: pass
class Finish: pass

################################### SCHEDULER ##################################

def yields_from(f):
    @functools.wraps(f)
    def run(*args):
        routine = f(*args)
        def routine_send(v):
            try: return routine.send(v)
            except StopIteration: return Finish
        def routine_throw(e=StopIteration):
            try: return routine.throw(e)
            except StopIteration: return Finish
        def my_next(yielded=None):
            if yielded is None:
                try: yielded = next(routine)
                except StopIteration:return
            if yielded is None:
                my_next()
            elif yielded is Callback:
                my_next(routine_send(lambda v: my_next(routine_send(v))))
            elif yielded is Cancel:
                my_next(routine_send(lambda: my_next(routine_throw())))
            elif isinstance(yielded, Delay):
                sublime.set_timeout(my_next, yielded)
            elif yielded in (AwaitCallback, Finish):
                return
        my_next()
    return run

#################################### HELPERS ###################################

def input_panel(caption="Input:",
                initial_text="",
                cancel=Finish ):

    panel = sublime.active_window().show_input_panel (
        caption, '', (yield Callback), None, (yield Cancel))
    
    panel.run_command('insert_snippet', dict(contents=initial_text))

    try:  return (yield AwaitCallback)
    except StopIteration:
        if cancel is Finish:  yield Finish
        else:  return None

def quick_panel(items, flags=0, selected_index=-1, cancel=Finish):
    show_panel = sublime.active_window().show_quick_panel
    show_panel( items=items, on_select=(yield Callback), flags=flags,
                             selected_index=selected_index )

    ix = (yield AwaitCallback)

    if ix == -1 and cancel is Finish:
        yield Finish
    else:
        return (-1, None) if ix == -1 else (ix, items[ix])

################################################################################