#coding: utf8
#################################### IMPORTS ###################################

# Sublime Libs
import sublime
import sublime_plugin

from .package_resources import norm_path_to_sublime_style

################################ HELPER COMMANDS ###############################

class GotoLineNumber(sublime_plugin.TextCommand):
    def run(self, edit, line):
        view = self.view
        view.sel().clear()
        line_region = sublime.Region(view.text_point(line-1, 0))
        
        view.sel().add(
            line_region
        )
        view.show(line_region, True)

class SelectRegions(sublime_plugin.TextCommand):
    def run(self, edit, regions, show_surrounds=True):
        view = self.view
        view.sel().clear()
        for r in regions:
            view.sel().add(sublime.Region(*r))
        
        if view.sel():
            view.show(view.line(view.sel()[0]).begin(), show_surrounds)

class OpenFileEnhanced(sublime_plugin.WindowCommand):
    def run(self, file, line=None, regions=None, **kw):
        fn = norm_path_to_sublime_style(file)
        
        window = self.window
        kw['file'] = fn
        window.run_command("open_file", kw)

        # The pseudo zip file View.file_name() will be this
        full_name = (fn.replace("${packages}/", 
                                   sublime.packages_path() + '/'))
        
        open_file_view = self.window.find_open_file(full_name)
        
        def do():
            if open_file_view.is_loading():
                sublime.set_timeout(do, 10)
            else:
                if line is not None:
                    open_file_view.run_command (
                        'goto_line_number', dict(line=line))
                elif regions is not None:
                    open_file_view.run_command (
                        'select_regions', dict( regions=regions, 
                                                show_surrounds=True ))
                window.focus_view(open_file_view)
                window.focus_group(window.get_view_index(open_file_view)[0])
        do()