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
from Default.indentation import normed_indentation_pt

# Edit Preferences imports
from .scheduler import yields_from, input_panel

################################### CONSTANTS ##################################

TAB_STOP_RE = r"(?<!\\)\$(%s)|\$\{(%s)(?::|/)"
TAB_STOP = re.compile(TAB_STOP_RE % ('\\d+', '\\d+'))

################################### SETTINGS ###################################

def get_setting(s, d=None):
    settings = sublime.load_settings("edit-preferences.sublime-settings")
    return settings.get(s, d)

def get_snippets_path():
    return get_setting('extracted_snippets_json_path')

############################### INVERSION HELPERS ##############################

def inversion_stream(view, regions, start=None, end=None):
    n = (len(regions) * 2) - 1

    end   = end   or view.size()
    start = start or 0

    def inner():
        for reg in regions:
            yield reg.begin()
            yield reg.end()

    for i, pt in enumerate(inner()):
        if i == 0:
            if pt == start: continue
            else:       yield start

        elif i == n:
            if pt != end:
                yield pt
                yield end

            continue

        yield pt

def invert_regions(view=None, regions=[], spanning=False):
    inverted = []

    if spanning is not False: # regions empty eval as False
        span_start = spanning.begin()
        span_end   = spanning.end()
    else:
        span_start = None
        span_end = None

    for i, pt in enumerate(inversion_stream(view, regions, span_start, span_end)):
        if i%2 == 0: start = pt
        else: inverted.append(sublime.Region(start, pt))

    return inverted or [sublime.Region(0, 0)]

################################ CREATE SNIPPET ################################

def shares_extents(r1, r2):
    return set([r1.a, r1.b]).intersection(set([r2.a, r2.b]) )

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

############################## INCREMENT TAB STOPS #############################

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

class IncrementTabstops(sublime_plugin.TextCommand):
    def run(self, edit, args=[]):
        view = self.view
        for sel in view.sel():
            selection = view.substr(sel)
            view.replace (
                edit, sel, replace_highest(increment_tabstops(selection)))

################################ EXTRACT SNIPPET ###############################

def scope_as_snippet(view):
    scope = view.scope.split()
    return '${1:%s}${2: %s}' % (scope[0], ' '.join(scope[1:]))

def load_snippets():
    with open(get_snippets_path(), 'r') as fh:
        try:
            the_snippets = json.load(fh)
        except ValueError:
            the_snippets = []
        return the_snippets

class ExtractedSnippetsCompletions(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations, flags = 0):
        if ( not prefix or 
             not get_setting('extracted_snippets_completions') or
             not get_snippets_path() ): return []

        completions = [
            ("%(trigger)s\t(SnippetCompletions)" %  s, s['contents']) for
             s in load_snippets() if 'scope' not in s or any(
             view.match_selector(p, s['scope']) for p in locations) ]

        if view.match_selector(locations[0], 'source.js'):
            extra = view.extract_completions(prefix, locations[0])
            completions.extend(("%s\t(buffer)" % e, e) for e in extra)

        return (completions, flags )

class ExtractSnippetCommand(sublime_plugin.TextCommand):
    def is_enabled(self, args=[]):
        return bool( (self.view.sel() or 
                      self.view.get_regions('auto_select')) and 
                      get_snippets_path() )

    @yields_from
    def run(self, edit):
        view   = self.view
        window = view.window()
        view.run_command('auto_select', dict(cmd='merge'))

        contents     = extract_snippet(view, edit)
        scope        = scope_as_snippet(view)
        the_snippets = load_snippets()

        the_snippets.append( dict(
            scope    = (yield from input_panel('Enter Scope',   scope)),
            trigger  = (yield from input_panel('Enter Trigger', '')),
            uuid     = uuid.uuid1().hex,
            contents = contents ))

        with open(get_snippets_path(), 'w') as fh:
            json.dump( sorted(the_snippets, key=lambda s: s['trigger']),
                       fh, indent=4 )

################################################################################