#coding: utf8
#################################### IMPORTS ###################################


# Std Libs
import json
import functools
# import re

from contextlib import contextmanager

# from  json.scanner import py_make_scanner as make_scanner
from json.decoder import JSONDecoder
from json.scanner import NUMBER_RE

#################################### ROWCOL ####################################

class Boolean(object):
    def __init__(self, value):
        self.value = bool(value)
    def __bool__(self):
        return self.value
    def __str__(self):
        return str(self.value).lower()

# For strings
def inner(s):  return s.__start__,   s.__end__   -1
def outer(s):  return s.__start__-1, s.__end__
def linner(s): return s.__start__+1, s.__end__  -1
def louter(s): return s.__start__,   s.__end__  +1
def iinner(s): return s.__start__,   s.__end__
def iouter(s): return s.__start__,   s.__end__

members = {'__end__':0, '__start__': 0, '__inner__' : inner, '__outer__': outer}

COL_JSON = dict (
    (obj, type(obj.__name__, (obj, ), members)) for obj in
    ( dict, list, int, float, str ) )

COL_JSON[bool] = type('bool', (Boolean, ), members)

for obj in (dict, list):
    COL_JSON[obj].__inner__ = linner
    COL_JSON[obj].__outer__ = louter

for obj in (int, float, bool):
    COL_JSON[obj].__inner__ = iinner
    COL_JSON[obj].__outer__ = iouter

dumps = functools.partial(json.dumps, default = lambda o: o.value)

def col_val(val, end, pend):
    cls = type(val)
    if cls in COL_JSON:
        val = COL_JSON[cls ](val)
        val.__end__ = end
        val.__start__ = pend

    return val

#################################### SANITY ####################################

def json_filter(text):
    i=0
    n=len(text)

    while i < n:
        c = text[i]
        i+=1

        if c == '"':
            yield c

            while i < n:
                c = text[i]
                i += 1

                if c == "\\":
                    yield c
                    if i < n:
                        yield text[i]
                        i+=1
                elif c == '"':
                    yield c
                    break
                else:
                    yield c

        elif c == '/':
            try:
                next_char = text[i]
            except IndexError:
                yield c # Let the proper json parser blow up with error report
                continue

            token = c+next_char

            if token == "//":
                i-=1
                while i < n and text[i] != '\n':
                    yield ' '
                    i+=1
                yield '\n'
                i+=1
            elif token == "/*":
                i-=1
                while i < n and not (text[i] == '*' and text[i+1] == '/'):
                    yield ' '
                    i+=1
                yield '  '
                i+=1
        elif c == ',':
            buf = [c]

            while i < n:
                c=text[i]
                buf.append(c)
                i+=1

                if c.isspace():
                    continue
                elif c in ']}':
                    buf[0] = ' '
                    break
                else:
                    buf.pop()
                    i-=1
                    break

            for c in buf:
                yield c
        else:
            yield c

def sanitize_json(text):
    sanitized = ''.join(json_filter(text))
    assert len(sanitized) == len(text)
    return sanitized

def strip_json_comments(text):
    return sanitize_json(text)

################################################################################

scan_string = json.decoder.scanstring

@functools.wraps(scan_string)
def col_string(s, end, *args, **kw):
    val, ix = scan_string(s, end, *args, **kw)
    return col_val(val, ix, end), ix

DEBUG_OUT = True

################################# MAKE SCANNER #################################

def make_scanner(context):
    parse_object = context.parse_object
    parse_array = context.parse_array
    parse_string = col_string
    match_number = NUMBER_RE.match
    strict = context.strict
    parse_float = context.parse_float
    parse_int = context.parse_int
    parse_constant = context.parse_constant
    object_hook = context.object_hook
    object_pairs_hook = context.object_pairs_hook
    memo = context.memo

    def _scan_once(string, idx):
        try:
            nextchar = string[idx]
        except IndexError:
            raise StopIteration

        return_ = None
        if nextchar == '"':
            return_ = parse_string(string, idx + 1, strict)
        elif nextchar == '{':
            return_ = parse_object((string, idx + 1), strict,
                _scan_once, object_hook, object_pairs_hook, memo)
        elif nextchar == '[':
            return_ = parse_array((string, idx + 1), _scan_once)
        elif nextchar == 'n' and string[idx:idx + 4] == 'null':
            return_ = None, idx + 4
        elif nextchar == 't' and string[idx:idx + 4] == 'true':
            return_ = True, idx + 4
        elif nextchar == 'f' and string[idx:idx + 5] == 'false':
            return_ = False, idx + 5

        if return_:
            val, ix = return_
            return col_val(val, ix, idx), ix

        m = match_number(string, idx)
        if m is not None:
            integer, frac, exp = m.groups()
            if frac or exp:
                res = parse_float(integer + (frac or '') + (exp or ''))
            else:
                res = parse_int(integer)
            return_ = res, m.end()
        elif nextchar == 'N' and string[idx:idx + 3] == 'NaN':
            return_ = parse_constant('NaN'), idx + 3
        elif nextchar == 'I' and string[idx:idx + 8] == 'Infinity':
            return_ = parse_constant('Infinity'), idx + 8
        elif nextchar == '-' and string[idx:idx + 9] == '-Infinity':
            return_ = parse_constant('-Infinity'), idx + 9
        else:
            raise StopIteration
        val, ix = return_
        return col_val(val, ix, idx), ix

    def scan_once(string, idx):
        try:
            return _scan_once(string, idx)
        finally:
            memo.clear()

    return _scan_once

################################################################################

class JSONIXDecoder(JSONDecoder):
    def __init__(self):
        JSONDecoder.__init__(self, strict=False)
        self.scan_once = make_scanner(self)

@contextmanager
def decode_with_ix():
    try:
        json.decoder.scanstring = col_string
        yield
    finally:
        json.decoder.scanstring = scan_string

loads = functools.partial(json.loads, cls=JSONIXDecoder)

if 0:
    with decode_with_ix():
        print ("*" * 80)
        test_case = '[ "keys"]'
        a_str = list(json.loads(test_case, cls=JSONIXDecoder))[0]

        print (a_str)
        print (type(a_str))

if 1:
    with decode_with_ix():

        b = Boolean(False)
        assert dumps([True, b]) == '[true, false]'
        assert not b

        assert type(list(loads('{"keys":5}').keys())[0]).__qualname__ == COL_JSON[str].__qualname__
        assert type(loads('["ctrl+shift"]')[0]).__qualname__ == COL_JSON[str].__qualname__

        v = '[ "ctrl+shift"]'
        ju = loads(v)[0]

        # print (type(ju))

        # print(repr(v[slice(*ju.__inner__())]))
        assert v[slice(*ju.__inner__())] == 'ctrl+shift'
        assert v[slice(*ju.__outer__())] == '"ctrl+shift"'

        ju = loads(v)
        assert v[slice(*ju.__inner__())] == ' "ctrl+shift"'
        assert v[slice(*ju.__outer__())] == v

        v = '{  "key": [1,2,3,4] }'
        ju = loads(v)
        # print (type(ju))

        assert v[slice(*ju.__inner__())] == '  "key": [1,2,3,4] '
        assert v[slice(*ju.__outer__())] == v

        # print (type(list(ju.keys())[0]) )
        # print (type(ju["key"]))

        assert v[slice(*ju["key"].__outer__())] == '[1,2,3,4] '
        # # assert
        assert v[slice(*ju["key"][0].__inner__())] == '1'
        assert v[slice(*ju["key"][0].__outer__())] == '1'
        #  # == '1'

        v = '{  "key": [1.055,2,3,4] }'
        ju = loads(v)

        assert v[slice(*ju["key"][0].__inner__())] == '1.055'
        assert v[slice(*ju["key"][0].__outer__())] == '1.055'


        v = '{  "key": false }'
        ju = loads(v)

        # print (type(ju["key"]))
        # print ((ju["key"].__inner__()))
        
        
        
        
        v = '{  "key": "", "key2" : true }'
        ju = loads(v)

        assert v[slice(*ju["key"].__inner__())] == ''
        assert v[slice(*ju["key"].__outer__())] == '""'
        assert v[slice(*ju["key2"].__outer__())] == 'true'

        
        
        
        
        
        
        
        
        
        
