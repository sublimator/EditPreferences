import sublime
import sublime_api

def plugin_loaded():
    try:
        sublime.Selection.__getitem__.__patched__
        return
    except AttributeError:
        pass

    def __getitem__(self, index):
        if index == -1: index += sublime_api.view_selection_size(self.view_id)

        r = sublime_api.view_selection_get(self.view_id, index)
        if r.a == -1:
            raise IndexError()
        return r

    __getitem__.__patched__ = True

    sublime.Selection.__getitem__ = __getitem__
