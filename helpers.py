#coding: utf8
#################################### IMPORTS ###################################

# Std Libs
import re
import os
import glob
import zipfile

from os.path import normpath, split, join, isdir, splitext, basename, dirname
from collections import defaultdict
# from pprint import pprint

# Sublime Libs
import sublime
import sublime_plugin

################################### CONSTANTS ##################################

PREFIX_ZIP_PACKAGE_RELATIVE = re.compile("(?P<prefix>.*)/"
                                         "(?P<package>.*?)\.sublime-package/"
                                         "(?P<relative>.*)")

#################################### HELPERS ###################################

def view_related_packages(view):
    """
    
    :view:
    
        A sublime.View object

    Returns a list of simple package names,
    
         eg. ["Default", "Python"]
    
    
    Packages will meet the criteria:
    
        * container package for the view's syntax
        * container package for the view's underlying file

    """
    try: fn = view.file_name()
    except: return []

    pkg_path = normpath(sublime.packages_path())
    dirs = []

    if fn and normpath(fn).startswith(pkg_path):
        dirs.append(split(fn[len(pkg_path)+1:])[0])

    syntax = view.settings().get("syntax")
    syntax_package = syntax.split('/')[1]

    dirs.append(syntax_package)

    return dirs

def enumerate_installed_packages():
    """
    
    return 
        
        A list of dicts()
        
        
        eg.  
        [
            {"zip": False, "name": "User"},
            {"zip": "$abs_path_to_sublime_package_zip", "name": "Default"}
        ]

    """

    zipped_package_locations = []
    near_executable          = join(dirname(sublime.executable_path()),
                                    'Packages')
    zipped_package_locations = [ near_executable,
                                 sublime.installed_packages_path()]

    installed_packages       = ([
        {"zip" : False, "folder" : join(sublime.packages_path(), d),
          "name" : d}
          for d in os.listdir(sublime.packages_path())
        if isdir (join(sublime.packages_path(), d))
    ])

    for location in zipped_package_locations:
        packages_pattern = location + '/*.sublime-package'
        packages = glob.glob(packages_pattern)

        for package in packages:
            package_info = dict (
                folder=False, zip=package, name=basename(splitext(package)[0]))
            installed_packages.append(package_info)

    return installed_packages

def package_info_lookup():
    """
    
    returns:
        A dict keyed by the package name with values of
            
            {zip : False or abspath, 
            folder: False or abspath }
    """

    mapping = defaultdict(dict)
    packages = enumerate_installed_packages()

    for package in packages:
        pkg = mapping[package["name"]]
        pkg["name"] = package["name"] # redundant but makes these self contained
        pkg["zip"]    = pkg.get("zip") or package["zip"]
        pkg["folder"] = pkg.get("folder") or package["folder"]

    return dict(mapping)

def contextual_packages_list(view=None):
    if view is None:
        view = sublime.active_window().active_view()

    contextual = view_related_packages(view)
    others = sorted(set((f["name"] for f in enumerate_installed_packages()
                       if f["name"] not in contextual)),
                      key = lambda f: f.lower())
    
    ignored = set((sublime.load_settings('Preferences.sublime-settings')
                         .get('ignored_packages')))

    return [f for f in (contextual + others) if f not in ignored]

def list_package_dir(package_info):
    """

    returns:
        A dict keyed by the file name with values of

            {
            name:  basename of file
            zip_file : False or abspath, 
            folder_file: False or abspath }

    """

    zip_file = package_info['zip']
    folder = package_info['folder']

    zip_files = []

    if zip_file:
        z = zipfile.ZipFile(zip_file, 'r')
        zip_files = sorted([i.filename for i in z.infolist() if not '/' in i.filename])
        z.close()

    contents = defaultdict (
            lambda: dict (
            name = None,
            zip_path=False, 
            folder_path=False ))

    for f in zip_files:
        f_info = contents[f]
        f_info['name'] = f
        f_info['zip_path'] = os.path.join(zip_file, f)

    if folder:
        for f in os.listdir(folder):
            f_info = contents[f]
            
            f_info['name'] = f
            f_info['folder_path'] = os.path.join(folder, f)

    return contents

def package_file_contents(fn):
    m = PREFIX_ZIP_PACKAGE_RELATIVE.search(fn)
    if m is not None:
        zip_file = "%(prefix)s/%(package)s.sublime-package" % m.groupdict()
        z = zipfile.ZipFile(zip_file, 'r')
        try:
            f = m.groupdict()['relative']
            return z.read(f).decode('utf-8')
        finally:
            z.close()
    else:
        with open(fn, 'r', encoding='utf-8') as fh:
            return fh.read()

def testicle():
    # the_view = sublime.active_window().active_view()
    # print (repr(the_view))
    # print (view_related_packages(the_view))
    # print ("FFFF")
    from pprint import pprint
    # import pprint
    # pprint.pprint (enumerate_installed_packages())
    print (contextual_packages_list())
    # print (package_info_lookup())


    # path = "/home/nick/sublime_text_3/Packages/Default.sublime-package"

    # lookup = package_info_lookup()
    # ff = list_package_dir(lookup["Default"])
    
    # pprint(ff)
    
    # for pkg, name, f in glob_packages('sublime-settings'):
    #     print ("f", f, pkg)

    # pprint(lookup)

    # pprint(list_package_dir(lookup["Default"]))

    # z = zipfile.ZipFile(path, 'r')
    # files = sorted([i.filename for i in z.infolist() if not '/' in i.filename])
    # z.close()
    
    
    # pprint(list(glob_packages('sublime-settings')))

    # pprint (files)

    # self.contents = {"":""}

    # for f in files:
    #     base, ext = os.path.splitext(f)
    #     if ext != ".py":
    #         continue

    #     paths = base.split('/')

    #     self.contents['.'.join(paths)] = z.read(f).decode('utf-8')

    #     paths.pop()
    #     while len(paths) > 0:
    #         self.contents['.'.join(paths)] = ""
    #         paths.pop()

# sublime.set_timeout(testicle)

##################################### TODO #####################################

def glob_packages(file_type='sublime-keymap', view=None):
    
    if isinstance(file_type, str):
        file_type = file_type.replace('%PLATFORM%', sublime.platform())
        if '.' not in file_type:
            file_type = '.*\.%s$' % file_type
        file_type = re.compile(file_type)

    lookup = package_info_lookup()

    for pkg in contextual_packages_list(view):
        pkg_info = lookup[pkg]

        found_files = []
        for f, file_info in sorted(list_package_dir(pkg_info).items()):

            if file_type.match(f):
                if file_info['folder_path']:
                    found_files.append(file_info['folder_path'])
                else:
                    found_files.append(file_info['zip_path'])

        for f in found_files:
            yield pkg, splitext(basename(f))[0], f

################################################################################


# print (list(glob_packages()))

def normalise_to_open_file_path(file_name):
    """
    
    :file_name:
    
        A str that could actually be a pseudo path to a file nested inside a
        `sublime-package` file.
    
    The command `open_file` has magic to open file contained in zip files, or in
    extracted folder overrides.
    
    """

    m = PREFIX_ZIP_PACKAGE_RELATIVE.search(file_name )
    if m is not None:
        return "${packages}/%(package)s/%(relative)s" % m.groupdict()
    else:
        return file_name

# print (normalise_to_open_file_path('/home/nick/sublime_text_3/Packages/Vintage.sublime-package/Default (Linux).sublime-keymap'))

def plugin_name(plug_class):
    """
    
    :plug_class:
    
        A sublime_plugin.Command or sublime_plugin.EventListener class
        NOT instance.
        
    In python 2, you could do some magic to create a faux instance of the
    plug_class to pass it to `sublime_plugin.Command.name()` as `self`, but I've
    as yet been unable to do it in Py 3.
    
    So, we have to duplicate a bit of code from sublime_plugin.py that has
    dependencies on more than it needs.

    """

    if not issubclass(plug_class, sublime_plugin.Command):
        return plug_class.__name__
    else:
        def name(clsname):
            name = clsname[0].lower()
            last_upper = False
            for c in clsname[1:]:
                if c.isupper() and not last_upper:
                    name += '_'
                    name += c.lower()
                else:
                    name += c
                last_upper = c.isupper()
            if name.endswith("_command"):
                name = name[0:-8]
            return name

        return name(plug_class.__name__)

class temporary_event_handler(object):
    """
    
    """

    def __init__(self, cb, event):
        setattr(self, event, cb)
        self.callbacks = sublime_plugin.all_callbacks[event]
        self.callbacks.append(self)

    def remove(self):
        sublime.set_timeout(lambda: self.callbacks.remove(self), 0)

def select(view, region, show_surrounds=True):
    sel_set = view.sel()
    sel_set.clear()
    sel_set.add(region)
    view.show(region, show_surrounds)
