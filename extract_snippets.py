################################################################################

# Std Libs
import textwrap
import re
import json
import bisect
import uuid

# Sublime Libs
import sublime
import sublime_plugin

# Sublime Default libs
from Default.indentation import normed_indentation_pt

# Edit Preferences imports
from .scheduler import yields_from, input_panel
from .helpers import inversion_stream, invert_regions, get_setting

################################### CONSTANTS ##################################

EXTRACTED_SNIPPETS_SETTING = 'extracted-snippets.sublime-settings'
TAB_STOP_RE = r"(?<!\\)\$(%s)|\$\{(%s)(?::|/)"
TAB_STOP = re.compile(TAB_STOP_RE % ('\\d+', '\\d+'))

################################### COMMANDS ###################################

class ExtractSnippetCommand(sublime_plugin.TextCommand):
    def is_enabled(self, args=[]):
        return bool( (self.view.sel() or
                      self.view.get_regions('auto_select')) )

    @yields_from
    def run(self, edit):
        view   = self.view
        window = view.window()

        view.run_command('auto_select', dict(cmd='merge'))
        settings = sublime.load_settings(EXTRACTED_SNIPPETS_SETTING)

        contents     = extract_snippet(view, edit)
        scope        = scope_as_snippet(view)
        the_snippets = settings.get('extracted_snippets')

        the_snippets.append( dict(
            scope    = (yield from input_panel('Enter Scope',   scope)),
            trigger  = (yield from input_panel('Enter Trigger', '')),
            uuid     = uuid.uuid1().hex,
            contents = contents ))

        settings.set("extracted_snippets", the_snippets)
        sublime.save_settings(EXTRACTED_SNIPPETS_SETTING)

class IncrementTabstops(sublime_plugin.TextCommand):
    def run(self, edit, args=[]):
        view = self.view
        for sel in view.sel():
            selection = view.substr(sel)
            view.replace (
                edit, sel, replace_highest(increment_tabstops(selection)))

################################### LISTENERS ##################################

class ExtractedSnippetsCompletions(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations, flags = 0):
        if not prefix or not get_setting('extracted_snippets_completions'):
            return []

        completions = [
            ("%(trigger)s\t(SnippetCompletions)" %  s, s['contents']) for
             s in load_snippets() if 'scope' not in s or any(
             view.match_selector(p, s['scope']) for p in locations) ]

        if view.match_selector(locations[0], 'source.js'):
            extra = view.extract_completions(prefix, locations[0])
            completions.extend(("%s\t(buffer)" % e, e) for e in extra)

        return (completions, flags )

############################ EXTRACT SNIPPET HELPERS ###########################

def shares_extents(r1, r2):
    return {r1.a, r1.b} & {r2.a, r2.b}

def extract_snippet(view, edit):
    # Reset start end_points
    span               = view.sel()[0].cover(view.sel()[-1])
    tab_stops          = [s for s in view.sel() if not
                          (shares_extents(s, span) and s.empty())]
    snippet            = [ normed_indentation_pt(view, span, non_space=True) *
                           ' ']
    tab_stop_map       = {}
    i                  = 0

    for region in [ sublime.Region(r.begin(), r.end(), 666) for r in
                    invert_regions(regions=tab_stops, spanning=span) ]:
        bisect.insort(tab_stops, region)

    for region in tab_stops:
        text = (view.substr(region)
                    .replace('\\', '\\\\')
                    .replace('$', '\\$'))
        i+=1

        if region.xpos != 666:
            tab_stop_index = tab_stop_map.get(text, i)
            if tab_stop_index == i and text: tab_stop_map[text] = i
            text = '${%s:%s}' % (tab_stop_index, text.replace('}', '\\}'))

        snippet.append(text)

    return textwrap.dedent(''.join(snippet)).lstrip()

def scope_as_snippet(view):
    scope = view.scope.split()
    return '${1:%s}${2: %s}' % (scope[0], ' '.join(scope[1:]))

def load_snippets():
    settings = sublime.load_settings(EXTRACTED_SNIPPETS_SETTING)
    return settings.get("extracted_snippets", [])

########################### INCREMENT TAB STOP HELPES ##########################

def inc_stop(m):
    return re.sub('\d+', lambda d: str(int(d.group()) + 1), m)

def increment_tabstops(s):
    return TAB_STOP.sub(lambda m: inc_stop(m.group()), s)

def zero_stop(s, replace):
    return re.sub(replace, '0', s)

def replace_highest(s):
    h = str(max(int(max(g)) for g in TAB_STOP.findall(s)))

    return re.sub (
        TAB_STOP_RE % (h,h),
        lambda m: '%s' % zero_stop(m.group(), h),
        s )

################################################################################