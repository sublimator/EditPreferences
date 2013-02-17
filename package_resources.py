#coding: utf8
#################################### IMPORTS ###################################

# Std Libs
import codecs
import functools
import glob
import os
import re
import pprint
import sys
import unittest
import zipfile

from os.path import normpath, split, join, isdir, splitext, basename, dirname
from collections import defaultdict

# Sublime Libs
import sublime
import sublime_plugin

try:         import nose
except ImportError: nose = None

#################################### EXPORTS ###################################

__all__ =  ['PATH_ABSOLUTE',
            'PATH_CONFIG_RELATIVE',
            'PATH_ZIPFILE_PSEUDO',
            'ST2',
            'ST3',
            'norm_path_to_sublime_style',
            'decompose_package_file_path',
            'executable_relative_packages_path',
            'package_file_binary_contents',
            'package_file_contents',
            'package_file_exists',
            'package_file_path_to_open_file_path',
            'platform_specifier',
            'zipped_package_locations']

################################### CONSTANTS ##################################

PREFIX_ZIP_PACKAGE_RELATIVE = re.compile("(?P<prefix>.*)/"
                                         "(?P<package>.*?)\.sublime-package/"
                                         "(?P<relative>.*)")

ST2 = sublime.version()[:1] == '2'
ST3 = not ST2

PATH_CONFIG_RELATIVE, PATH_ABSOLUTE, PATH_ZIPFILE_PSEUDO = range(3)

################################################################################
"""

**(Non exhaustive)** Brief:

@Efficient

@Globbing a whole list of packages for files that match a pattern:

    - possibly in nested folders

    - @Listing contents of a Package, files of which may be spread across an
        a .sublime-package, with overrides in an actual folder in 
        sublime.packages_path()

@Normalising paths to sublime style paths

    - /C/windows/system32 

"""
#################################### HELPERS ###################################

class bunch(dict):
    def __init__(self, *args, **kw):
        dict.__init__(self, *args, **kw)
        self.__dict__ = self

def platform_specifier():
    platform = sublime.platform().title()
    if platform == 'Osx': return 'OSX'
    return platform

def executable_relative_packages_path():
    return join(dirname(sublime.executable_path()), 'Packages')

def zipped_package_locations():
    return [ sublime.installed_packages_path(),
             executable_relative_packages_path() ]

################################# PATH HELPERS #################################

def zip_path_components(pth):
    """
    >>> d=zip_path_components(r"C:\\fuck\\fuck.sublime-package\\two.txt")
    >>> d['prefix']
    'C:/fuck'
    >>> d['relative']
    'two.txt'
    >>> d['package']
    'fuck'
    
    """
    m = PREFIX_ZIP_PACKAGE_RELATIVE.search(re.sub(r'\\', '/', pth))
    if m is not None:
        return m.groupdict()

def decompose_package_file_path(pth):
    """
    
    >>> tc = decompose_package_file_path
    >>> tc("Packages/Fool/one.py")
    ('Fool', 'one.py', 0, None)
    
    """

    if pth.startswith("Packages/"):
        _, package, relative = pth.split("/", 2)
        return package, relative, PATH_CONFIG_RELATIVE, None

    m = zip_path_components(pth)
    if m is not None:
        return m['package'], m['relative'], PATH_ZIPFILE_PSEUDO, m['prefix']
    else:
        pth = pth[len(sublime.packages_path())+1:]
        pkg, relative = pth.split("/", 1)
        return pkg, relative, PATH_ABSOLUTE, sublime.packages_path()

def norm_path_to_sublime_style(fn):
    """
    Formats a path as /C/some/path/on/windows/no/colon.txt that is suitable to
    be passed as the `file` arg to the `open_file` command.
    """
    fn = normpath(fn)
    fn = re.sub('^([a-zA-Z]):', '/\\1', fn)
    fn = re.sub(r'\\', '/', fn)
    return fn

def package_file_path_to_open_file_path(file_name):
    """
    
    >>> pth = '/Packages/Vintage.sublime-package/Default (Linux).sublime-keymap'
    >>> package_file_path_to_open_file_path(pth)
    '${packages}/Vintage/Default (Linux).sublime-keymap'
    
    :file_name:
    
        A str that could actually be a pseudo path to a file nested inside a
        `sublime-package` file or 
    
    The command `open_file` has magic to open file contained in zip files, or in
    extracted folder overrides.
    
    """

    file_name = norm_path_to_sublime_style(file_name)
    pkg, relative, pth_type, _ = decompose_package_file_path(file_name)
    return ( file_name if pth_type is PATH_ABSOLUTE else
             "${packages}/%s/%s" % (pkg, relative) )

############################ PACKAGE_FILE_* HELPERS ############################

def _package_file_helper(fn, encoding='utf-8', only_exists=False):
    pkg, path, pth_type, _ = decompose_package_file_path(fn)

    if pth_type == PATH_CONFIG_RELATIVE:
        pkg_path = os.path.join(sublime.packages_path(), pkg)
        fn = os.path.join(pkg_path, path)
        pth_type = PATH_ABSOLUTE

    if pth_type == PATH_ABSOLUTE:
        if only_exists and os.path.exists(fn):
            return True # could fall through to zip code
        else:
            if encoding is None: kw = dict(mode='rb')
            else:                kw = dict(mode='rU', encoding=encoding)

            try:
                with codecs.open(fn, **kw) as fh:
                    return fh.read()
            except IOError:
                if os.path.exists(fn):
                    raise

    for base_pth in zipped_package_locations():
        zip_path = os.path.join(base_pth, pkg + '.sublime-package')
        if not os.path.exists(zip_path): continue

        with zipfile.ZipFile(zip_path, 'r') as zh:
            try:
                zip_info = zh.getinfo(path)
            except KeyError:
                continue

            if only_exists:
                return True
            else:
                text = bytes = zh.read(zip_info)
                if encoding:
                    text = bytes.decode('utf-8')
                return text

def package_partial(**kw):
    return functools.partial(_package_file_helper, **kw)

package_file_exists = package_partial(only_exists=True)
package_file_contents = _package_file_helper
package_file_binary_contents = package_partial(encoding=None)

########################## PACKAGE LISTING / GLOBBING ##########################

def enumerate_virtual_package_folders():
    """
    
    Note that a package may appear more than once in this list.
    
    An abstract Package consist of a sublime-package sitting in one of the 
    `zipped_package_locations()` and also various overrides in a folder 
    on `sublime.packages_path()`
    
    """
    installed_packages       = ([

            # We make redundant info here, so later we know this
            bunch( zip_path    = False,
                   folder_path = join(sublime.packages_path(), d),
                   pkg_name    = d )
        for
            d in os.listdir(sublime.packages_path())
        if
            isdir (join(sublime.packages_path(), d))
    ])

    for location in zipped_package_locations():
        packages_pattern = location + '/*.sublime-package'
        packages = glob.glob(packages_pattern)

        for package in packages:
            package_info = bunch (
                folder_path=False,
                zip_path=package,
                pkg_name=basename(splitext(package)[0]))
            installed_packages.append(package_info)

    return installed_packages

def create_virtual_package_lookup():
    """
    :return:
        A dict of {pkg_name : {zip_path: '', folder_path: '', pkg_name : ''}}
        
        ie.  {pkg_name : merged_package_info}
    """
    mapping = defaultdict(bunch)
    packages = enumerate_virtual_package_folders()

    for package in packages:
        pkg = mapping[package.pkg_name]

        pkg.pkg_name  = package.pkg_name
        pkg.zip_path     = pkg.get("zip") or package.zip_path
        pkg.folder_path  = pkg.get("folder") or package.folder_path

    return dict(mapping)

# TODO: a `yielding` helper, can be used to search for a single file?
def list_virtual_package_folder(merged_package_info, matcher=None):
    zip_file = merged_package_info['zip_path']
    folder = merged_package_info['folder_path']
    zip_files = []

    if zip_file:
        with  zipfile.ZipFile(zip_file, 'r') as z:
            zip_files = sorted (z.namelist())

    contents = defaultdict(lambda: bunch( relative_name = None,
                                          zip_path=False,
                                          folder_path=False ))
    for f in zip_files:
        f_info = contents[f]
        f_info.relative_name = f
        f_info.zip_path = os.path.join(zip_file, f)

    if folder:
        for root, dirnames, filenames in os.walk(folder):
            for i in range(len(dirnames)-1, -1, -1):
                if dirnames[i] in ('.svn', '.git', '.hg'):
                    del dirnames[i]

            for f in filenames:
                relative_name = os.path.join(root[len(folder) + 1:], f)

                f_info = contents[relative_name]
                f_info.relative_name  = relative_name
                f_info.folder_path  = os.path.join(root, f)

    if matcher is not None:
        contents = dict((k, v) for k,v in contents.items() if matcher(k))

    return contents

def glob_packages (
        file_type='sublime-keymap',
        package_sort_key=None,
        ignored_packages=True,
        ):
    """
    
    Will yield files in form PATH_ABSOLUTE or PATH_ZIPFILE_PSEUDO which
    have good performance characteristics when using package_file_contents.
    
    """
    
    if ignored_packages and ignored_packages is not True:
        ignored_packages = sublime.load_settings (
            'Preferences.sublime-settings').get('ignored_packages')

    if isinstance(file_type, str):
        file_type = file_type.replace('%PLATFORM%', platform_specifier())
        if '.' not in file_type:
            file_type = '.*\.%s$' % file_type
        file_type = re.compile(file_type)

    lookup =  create_virtual_package_lookup()

    for pkg in sorted(lookup, key=package_sort_key):
        pkg_info = lookup[pkg]
        found_files = []

        for f, file_info in sorted (
                    list_virtual_package_folder(pkg_info,
                    matcher=file_type.match ).items(), key=lambda t:t[0] ):

            if file_info['folder_path']:
                found_files.append(file_info['folder_path'])
            else:
                found_files.append(file_info['zip_path'])

        for f in found_files:
            yield pkg, splitext(basename(f))[0], f

##################################### TESTS ####################################

class GlobPackageTests(unittest.TestCase):
    """
    
    These tests are pretty vague, but at least exercise the code somewhat
    
    """
    def test_glob_packages(self):
        # pprint.pprint (
        list(glob_packages())
        # )

class Tests(unittest.TestCase):
    """
    
    These tests are pretty vague, but at least exercise the code somewhat
    
    """
    def test_enumerate_virtual_package_folders(self):
        enumerate_virtual_package_folders()

    def test_create_virtual_package_lookup(self):
        create_virtual_package_lookup()

    def test_list_virtual_package_folder(self):
        lookup = create_virtual_package_lookup()
        (list_virtual_package_folder(lookup['Java']))
        (list_virtual_package_folder(lookup['User']))

    def test_package_file_exists(self):
        self.assertTrue(package_file_exists("Packages/Default/sort.py"))

    def test_package_file_contents(self):
        # Relative path
        (package_file_contents (
                "Packages/PackageResources/package_resources.py"))

        # Absolute path
        (package_file_contents(( sublime.packages_path() +
                                "/PackageResources/package_resources.py")))


        # Relative path to zip contents
        ars = package_file_contents("Packages/Default/sort.py")
        nlen = len(ars)

        text="""\
def permute_selection(f, v, e):
    regions = [s for s in v.sel() if not s.empty()]
    regions.sort()"""

        self.assertIn(text, ars)

        if ST3:
            self.assertTrue(isinstance(ars, str))
        else:
            self.assertTrue(isinstance(ars, unicode))

        # Able to use PATH_ZIPFILE_PSEUDO (used by module.__file__)
        a= len( (package_file_contents(( executable_relative_packages_path() +
                                "/Default.sublime-package/sort.py"))))

        self.assertEquals(a, nlen)

    def test_package_file_binary_contents(self):
        ars = package_file_binary_contents("Packages/Default/sort.py")

        if ST3:
            self.assertTrue(isinstance(ars, bytes))
        else:
            self.assertTrue(isinstance(ars, str))

    def test_decompose_path(self):
        tc = decompose_package_file_path
        aseq = self.assertEquals

        r1 = (tc("Packages/Fool/one.py"))
        r2 = (tc("/Packages/Default.sublime-package/nested/sort.py"))
        r3 = (tc(sublime.packages_path() + "/Package/Nested/asset.pth"))

        aseq(r1[:-1], ('Fool', 'one.py',              PATH_CONFIG_RELATIVE))
        aseq(r2[:-1], ('Default', 'nested/sort.py',   PATH_ZIPFILE_PSEUDO))
        aseq(r3[:-1], ('Package', 'Nested/asset.pth', PATH_ABSOLUTE))

################ ONLY LOAD TESTS WHEN DEVELOPING NOT ON START UP ###############

try:               times_module_has_been_reloaded  += 1
except NameError:  times_module_has_been_reloaded  = -1       #<em>re</em>loaded

if 0 and times_module_has_been_reloaded:
    target = __name__

    if nose:
        nose.run(argv=[ 'sys.executable', target, '--with-doctest', '-s' ])
    else:
        suite = unittest.TestLoader().loadTestsFromName(target)
        unittest.TextTestRunner(stream = sys.stdout,  verbosity=0).run(suite)

    print ("running tests", target)
    print ('\nReloads: %s' % times_module_has_been_reloaded)

################################################################################