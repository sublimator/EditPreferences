#coding: utf8
#################################### IMPORTS ###################################

# Std Libs
import inspect
import os
from linecache import checkcache

# Sublime Libs
import sublime_plugin

from . helpers import plugin_name, temporary_event_handler
from . package_resources import norm_path_to_sublime_style,\
                                decompose_package_file_path,\
                               package_file_path_to_open_file_path

def package_name_and_package_relative_path(p):
    pkg, rel, _, __ = decompose_package_file_path(p)
    return pkg, rel

################################################################################

class ListCommands(sublime_plugin.WindowCommand):
    def run(self, args=[]):
        window = self.window
        commands = []
        completions = set()
        the_cmds = list(zip(('Application', 'Window', 'Text'),
                            sublime_plugin.all_command_classes ))

        the_cmds.extend([ (e, [type(c) for c in h]) for (e, h) in
                         list(sublime_plugin.all_callbacks.items())])

        for cmd_type, cmds in the_cmds:
            cmds = dict( ( plugin_name(t), t) for t in cmds)
            completions.add(cmd_type)

            for cmd_name, cmd in list(cmds.items()):
                completions.add(cmd_name)
                try:
                    f = os.path.normpath(inspect.getsourcefile(cmd))
                    pkg, relative = package_name_and_package_relative_path(f)
                    pkg = "%s/%s" % (pkg, relative)

                    commands += [(
                        (cmd_type, pkg, cmd_name),
                        f,
                        cmd
                    )]
                except Exception as e:
                    print ("ListCommands error", cmd, e)

        commands.sort(key=lambda i:i[0])
        display = ['/'.join(i[0]) for i in commands]

        ch = temporary_event_handler( lambda *a: [(c,c) for c in completions],
                                      'on_query_completions')
        def on_select(i):
            ch.remove()

            if i != -1:
                cmd = commands[i]
                cmd_type = cmd[0][0]

                obj = (
                    getattr(cmd[-1], cmd_type) if
                    cmd_type in sublime_plugin.all_callbacks else cmd[-1] )

                checkcache(cmd[1])

                line_num_one_based = inspect.getsourcelines(obj)[-1]
                file_name = os.path.normpath(cmd[1])
                file_name = package_file_path_to_open_file_path(file_name)

                window.run_command("open_file_enhanced",
                                    {"file" : (file_name),
                                     "line" : line_num_one_based})

        window.show_quick_panel(display, on_select, 1)
