#coding: utf8
#################################### IMPORTS ###################################

# Std Libs
import inspect
import os
from linecache import checkcache

# Sublime Libs
import sublime_plugin
import sublime

from . helpers import plugin_name, normalise_to_open_file_path

################################################################################

class ListCommands(sublime_plugin.WindowCommand):
    def run(self, args=[]):
        window = self.window
        commands = []
        sep = os.path.sep

        the_cmds = list(zip(('Application', 'Window', 'Text'),
                            sublime_plugin.all_command_classes ))

        the_cmds.extend([ (e, [type(c) for c in h]) for (e, h) in
                         list(sublime_plugin.all_callbacks.items())])

        for cmd_type, cmds in the_cmds:
            cmds = dict( ( plugin_name(t), t) for t in cmds)

            for cmd_name, cmd in list(cmds.items()):
                cmd = cmd

                try:
                    f = os.path.normpath(inspect.getsourcefile(cmd))
                    pkg = f.split(sep)[len(sublime.packages_path().split(sep))]

                    commands += [(
                        (cmd_type, pkg, cmd_name),
                        f,
                        cmd
                    )]
                except:
                    print (cmd)

        commands.sort(key=lambda i:i[0])
        display = ['/'.join(i[0]) for i in commands]

        def on_select(i):
            if i != -1:
                cmd = commands[i]
                cmd_type = cmd[0][0]

                obj = (
                    getattr(cmd[-1], cmd_type) if
                    cmd_type in sublime_plugin.all_callbacks else cmd[-1] )

                checkcache(cmd[1])

                line_num_one_based = inspect.getsourcelines(obj)[-1]
                file_name = os.path.normpath(cmd[1])
                file_name = normalise_to_open_file_path(file_name)
                
                window.run_command("open_file_enhanced", 
                    {"file" :  (file_name), 
                     "line" : line_num_one_based})

        window.show_quick_panel(display, on_select, 1)
