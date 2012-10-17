# -*- coding: utf-8 -*-
import os
import io
import re
import array
import codecs
import itertools

__all__ = ('DSLSource',)
#------------------------------------------------------------------------------#
# DSL Source                                                                   #
#------------------------------------------------------------------------------#
class DSLSource (object):
    """DSL (Lingvo) dictionary source
    """
    header_regex = re.compile (r'^#([^\s]*)\s*"([^"]*).*') # dictionary header


    def __init__ (self, filename):
        self.filename = filename
        self.stream = io.open (self.filename, 'rb')

        # size
        self.stream.seek (0, io.SEEK_END)
        self.stream_size = float (self.stream.tell ())
        self.stream.seek (0)

        # determine encoding
        bom = self.stream.read (max (len (codecs.BOM_UTF16_BE), len (codecs.BOM_UTF16_LE)))
        if bom.startswith (codecs.BOM_UTF16_BE):
            offset = len (codecs.BOM_UTF16_BE)
            self.decode = codecs.getdecoder ('utf-16be')
            self.newline = '\r\n'.encode ('utf-16be')
        elif bom.startswith (codecs.BOM_UTF16_LE):
            offset = len (codecs.BOM_UTF16_LE)
            self.decode = codecs.getdecoder ('utf-16le')
            self.newline = '\r\n'.encode ('utf-16le')
        else:
            offset = 0
            self.decode = codecs.getdecoder ('utf-8')
            self.newline = '\r\n'.encode ('utf-8')
        self.newline_size = len (self.newline)

        # headers
        self.offset = offset
        self.headers = {}
        for line, offset, size in self.lines (offset):
            match = self.header_regex.match (line)
            if not match:
                break
            self.offset = offset + size
            key, value = match.groups ()
            self.headers [key.lower ()] = value

    #--------------------------------------------------------------------------#
    # Validate                                                                 #
    #--------------------------------------------------------------------------#
    @classmethod
    def FromFile (cls, filename):
        """Create source from file if possible
        """
        if filename.lower ().endswith ('.dsl'):
            return cls (filename)

    #--------------------------------------------------------------------------#
    # Properties                                                               #
    #--------------------------------------------------------------------------#
    @property
    def Name (self):
        """Dictionary name
        """
        return self.headers.get ('name', os.path.basename (self.filename).rpartition ('.') [0])

    @property
    def Language (self):
        """Source and destination language pair
        """
        return (self.headers.get ('index_language', 'any'),
                self.headers.get ('contents_language', 'any'))

    #--------------------------------------------------------------------------#
    # Cards                                                                    #
    #--------------------------------------------------------------------------#
    word_regex        = re.compile (r'^[^\s]')      # beginning of the word
    word_ignore_regex = re.compile (r'\{[^}]*\}')   # ignore part of the word
    word_alt_regex    = re.compile (r'\(([^)]*)\)') # alternative part of the word
    word_space_regex  = re.compile (r'(\s)\s+')     # double spaces
    text_escape_regex = re.compile (r'\\(.)')       # escape
    tag_regex         = re.compile (r'(?<!\\)\[(/)?([^\]\s]+)(\s[^\]]+)?\]') # tag
    tag_map = {
        '\'' : 'stress',
        '*'  : 'fold',
        'b'  : 'bold',
        'c'  : 'color',
        'com': 'comment',
        'ex' : 'example',
        'i'  : 'italic',
        'p'  : 'type',      # part of speech
        'ref': 'link',
        'u'  : 'underline',
        's'  : 'sound',
        't'  : 'transcript',
        'trn': 'translation',
    }

    def Cards (self, report = None):
        """Iterate over available cards
        """
        lines = self.lines (self.offset)
        if report:
            report_value = [0]
            def report_changed (value):
                value = round (value, 3)
                if report_value [0] != value:
                    report_value [0] = value
                    report (value)
        else:
            report_changed = lambda _: None

        try:
            line, offset, size = next (lines)
            while True:
                #--------------------------------------------------------------#
                # Head                                                         #
                #--------------------------------------------------------------#
                head = []
                while self.word_regex.match (line):
                    head.append (line)
                    line = next (lines) [0]

                if not head:
                    break

                # parse
                words = []
                for word in head:
                    word = self.word_space_regex.sub (' ', self.word_ignore_regex.sub ('', word))
                    word_alts    = self.word_alt_regex.findall (word)
                    word_pattern = self.word_alt_regex.sub ('{}', word)
                    if word_alts:
                        word_alts.insert (0, '')
                        words.extend ((word_pattern.format (*(word_alts [(i + 1) * y] for i, y in enumerate (m))))
                                for m in itertools.product ((0, 1), repeat = len (word_alts) - 1))
                    else:
                        words.append (word)

                #--------------------------------------------------------------#
                # Body                                                         #
                #--------------------------------------------------------------#
                body = []
                try:
                    while not self.word_regex.match (line):
                        line = line.strip ()
                        if line:
                            if line.startswith ('[m'):
                                body.append (line)
                            else:
                                body.append ('[m0]')
                                body.append (line)
                                body.append ('[/m]')

                        line, stream_offset, size = next (lines)
                    report_changed (stream_offset / self.stream_size)
                except StopIteration:
                    report (1)

                body = ''.join (body)

                # parse
                def node_create (name, value = None, children = None):
                    node = {'name': name}
                    if name != 'text':
                        node ['children'] = []
                    if value is not None:
                        node ['value'] = value
                    return node

                offset, stack, match = 0, [node_create ('root')], None
                for match in self.tag_regex.finditer (body):
                    close, name, value = match.groups ()

                    # transform
                    if name.startswith ('m'):
                        value = int (name [1:]) if len (name) > 1 else 0
                        name  = 'indent'
                    else:
                        value = value and value.strip ()
                        name  = self.tag_map.get (name, name)
                    node = stack [-1]

                    # text
                    if offset < match.start ():
                        node ['children'].append (node_create ('text',
                            self.text_escape_regex.sub (r'\1', body [offset:match.start ()])))
                    offset = match.end ()

                    # node
                    if close:
                        node = stack.pop ()

                        # order
                        if not node ['name'].startswith (name):
                            # restore
                            stack.append (node)
                            # find match
                            shift = [(name, value)]
                            for index, node in enumerate (reversed (stack)):
                                if node ['name'].startswith (name):
                                    # shift nodes
                                    for node in stack [- index - 1:]:
                                        name, value = shift.pop ()

                                        node ['name'] = name
                                        if value is not None:
                                            node ['value'] = value
                                    break
                                else:
                                    shift.append ((node ['name'], node.get ('value')))
                            # unwind stack
                            node = stack.pop ()

                        # transcription
                        if name == 'transcript':
                            children = node ['children']
                            if len (children) == 1 and children [0]['name'] == 'text':
                                codes = array.array ('H')
                                codes.fromstring (children [0]['value'].encode ('utf-16le'))

                                node.pop ('children')
                                node ['value'] = ''.join (transcript_map.get (code, '?') for code in codes)

                    else:
                        child = node_create (name, value)
                        node ['children'].append (child)
                        stack.append (child)
                # tail
                if match:
                    if match.end () < len (body):
                        stack [-1]['children'].append (node_create ('text',
                            self.text_escape_regex.sub (r'\1', body [match.end ():])))
                else:
                    stack [-1]['children'].append (node_create ('text',
                        self.text_escape_regex.sub (r'\1', body)))

                root = stack [-1]
                del stack [:]

                # swap 'folds' with 'indents' and merge white spaces
                def walk_hoist (node):
                    if node ['name'] == 'fold':
                        parent = stack [-1]

                        # swap
                        if parent ['name'] == 'indent' and len (parent ['children']) == 1:
                            node ['name'],  parent ['name']  = parent ['name'],  node ['name']
                            node ['value'] = parent.pop ('value')

                            node   = parent
                            parent = stack [-2]

                        # merge spaces
                        parent_children = parent ['children']
                        index = parent_children.index (node) + 1
                        if index < len (parent_children):
                            node_left = parent_children [index]
                            if node_left ['name'] == 'text' and not len (node_left ['value'].strip ()):
                                parent_children.pop (index)
                                node ['children'].append (node_left)

                        return

                    stack.append (node)
                    for child in node ['children']:
                        if 'children' in child:
                            walk_hoist (child)
                    stack.pop ()

                walk_hoist (root)

                # merge adjoining folds
                get_is_fold = lambda node: node ['name'] == 'fold'
                def walk_join (node):
                    children = []
                    for is_fold, group in itertools.groupby (node ['children'], get_is_fold):
                        if is_fold:
                            fold = node_create ('fold')
                            for child in group:
                                fold ['children'].extend (child ['children'])
                            children.append (fold)
                        else:
                            for child in group:
                                children.append (child)
                                if 'children' in child:
                                    walk_join (child)
                    node ['children'] = children

                # walk_join (root)

                #--------------------------------------------------------------#
                # Yield                                                        #
                #--------------------------------------------------------------#
                yield {
                    'words': words,
                    'body': root
                }

        except StopIteration: pass

    #--------------------------------------------------------------------------#
    # Private                                                                  #
    #--------------------------------------------------------------------------#
    def lines (self, offset):
        """Lines starting from "offset"
        """
        data_tail = b''
        self.stream.seek (offset)
        while True:
            data = self.stream.read (1 << 12)
            if not data:
                break
            lines = (data_tail + data).split (self.newline)
            data_tail = lines.pop ()

            for line in lines:
                line, size = self.decode (line)
                yield line, offset, size + self.newline_size
                offset += size + self.newline_size

        line, size = self.decode (data_tail)
        yield line, offset, size

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        """Dispose source
        """
        self.stream.close ()

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

transcript_map = {code: value.decode ('utf-8') for code, value in {
    0x0020: b" ",                        # space
    0x0027: b'\'',                       # '
    0x0028: b'(',                        # (
    0x0029: b')',                        # )
    0x002c: b',',                        # ,
    0x002d: b'-',                        # -
    0x002e: b'.',                        # .
    0x002f: b'/',                        # /
    0x0030: b'\xc3\x9f',                 # ß ?
    0x0031: b'e\xcc\x83',                # ẽ ?
    0x0032: b'\xc9\x9c',                 # ɜ
    0x0033: b'\xc4\xa9',                 # ĩ ?
    0x0034: b'\xc3\xb5',                 # õ ?
    0x0035: b'\xc5\xa9',                 # ũ ?
    0x0036: b'\xca\x8e',                 # ʎ ?
    0x0037: b'\xc9\xa3',                 # ɣ ?
    0x0038: b'\xe1\xb5\x8a',             # e
    0x003a: b':',                        # ː
    0x003b: b';',                        # ;
    0x0041: b'A',                        # A
    0x0047: b'G',                        # G
    0x0048: b'H',                        # H
    0x004d: b'M',                        # M
    0x004e: b'N',                        # N
    0x004f: b'O',                        # O
    0x0052: b'R',                        # R
    0x0053: b'S',                        # S
    0x0054: b'T',                        # T
    0x0061: b'a',                        # a
    0x0062: b'b',                        # b
    0x0063: b'c',                        # c
    0x0064: b'd',                        # d
    0x0065: b'e',                        # e
    0x0066: b'f',                        # f
    0x0067: b'g',                        # g
    0x0068: b'h',                        # h
    0x0069: b'i',                        # i
    0x006a: b'j',                        # j
    0x006b: b'k',                        # k
    0x006c: b'l',                        # l
    0x006d: b'm',                        # m
    0x006e: b'n',                        # n
    0x006f: b'o',                        # o
    0x0070: b'p',                        # p
    0x0071: b'q',                        # q
    0x0072: b'r',                        # r
    0x0073: b's',                        # s
    0x0074: b't',                        # t
    0x0075: b'u',                        # u
    0x0076: b'v',                        # v
    0x0077: b'w',                        # w
    0x007a: b'z',                        # z
    0x0078: b'x',                        # x
    0x0079: b'y',                        # y
    0x00a0: b'\xca\xa7',                 # ʧ
    0x00a4: b'b',                        # b
    0x00a6: b'w',                        # w
    0x00a7: b'f',                        # f
    0x00a9: b's',                        # s
    0x00ab: b't',                        # t
    0x00ac: b'd',                        # d
    0x00ad: b'n',                        # n
    0x00ae: b'l',                        # l
    0x00b0: b'k',                        # k
    0x00b1: b'g',                        # g
    0x00b5: b'a',                        # a
    0x00b6: b'\xca\x8a',                 # ʊ
    0x00b7: b'\xc3\xa3',                 # ã
    0x00bb: b'\xc9\x99',                 # ə
    0x00df: b'\xc3\x9f',                 # ß
    0x00e3: b'\xc3\xa3',                 # ã
    0x00e4: b'\xc3\xa4',                 # ä
    0x00e6: b'\xc3\xa6',                 # æ
    0x00e7: b'\xc3\xa7',                 # ç
    0x00eb: b'\xc3\xab',                 # ë
    0x00f0: b'\xc3\xb0',                 # ð
    0x00f4: b'\xc3\xb4',                 # ô
    0x00f8: b'\xc3\xb8',                 # ø
    0x0101: b'\xc4\x81',                 # ā
    0x0113: b'\xc4\x93',                 # ē
    0x012b: b'\xc4\xab',                 # ī
    0x014b: b'\xc5\x8b',                 # ŋ
    0x014d: b'\xc5\x8d',                 # ō
    0x014f: b'\xc5\x8f',                 # ŏ
    0x0153: b'\xc5\x93',                 # œ
    0x01d0: b'\xc7\x90',                 # ǐ
    0x01d4: b'\xc7\x94',                 # ǔ
    0x0250: b'\xc9\x90',                 # ɐ
    0x0251: b'\xc9\x91',                 # ɑ
    0x0252: b'\xc9\x92',                 # ɒ
    0x0254: b'\xc9\x94',                 # ɔ
    0x0259: b'\xc9\x99',                 # ə
    0x025b: b'\xc9\x9b',                 # ɛ
    0x025c: b'\xc9\x9c',                 # ɜ
    0x0265: b'\xc9\xa5',                 # ɥ
    0x0272: b'\xc9\xb2',                 # ɲ
    0x0280: b'\xca\x80',                 # ʀ
    0x0283: b'\xca\x83',                 # ʃ
    0x028a: b'\xca\x8a',                 # ʊ
    0x028c: b'\xca\x8c',                 # ʌ
    0x028f: b'\xca\x8f',                 # ʏ
    0x0292: b'\xca\x92',                 # ʒ
    0x02a4: b'\xca\xa4',                 # ʤ
    0x02a7: b'\xca\xa7',                 # ʧ
    0x026a: b'\xc9\xaa',                 # ɪ
    0x02cc: b'\xcb\x8c',                 # ˌ
    0x02d0: b'\xcb\x90',                 # ː
    0x0303: b'\xcc\x83',                 # combining tilde
    0x0331: b'\xcc\xb1',                 # combining macron below
    0x035c: b'\xcd\x9c',                 # combining double breve below
    0x035d: b'\xcd\x9d',                 # combining double breve
    0x035e: b'\xcd\x9e',                 # combining double macron
    0x035f: b'\xcd\x9f',                 # combining double macron below
    0x03b8: b'\xce\xb8',                 # θ
    0x0402: b'i\xcb\x90',                # iː
    0x0403: b'\xc9\x91\xcb\x90',         # ɑː
    0x0404: b'z',                        # z
    0x0405: b'\xc5\x93\xcc\x83',         # œ̃
    0x0406: b'h',                        # h
    0x0407: b'r',                        # r
    0x0408: b'p',                        # p
    0x0409: b'\xca\x92',                 # ʒ
    0x040a: b'\xc5\x8b',                 # ŋ
    0x040b: b'\xce\xb8',                 # θ
    0x040c: b'u',                        # u
    0x040e: b'\xc9\xaa',                 # ɪ
    0x040f: b'\xca\x83',                 # ʃ
    0x0428: b'a',                        # a
    0x0440: b'\xc5\x8f',                 # ŏ
    0x0441: b'\xc9\xb2',                 # ɲ
    0x0442: b'\xc9\x94\xcc\x83',         # ɔ̃
    0x0443: b'\xc3\xb8',                 # ø
    0x0444: b'\xc7\x94',                 # ǔ
    0x0446: b'\xc3\xa7',                 # ç
    0x0447: b'a\xcd\x9ce',               # a͜e
    0x044a: b'\xca\x8f',                 # ʏ
    0x044c: b'\xc9\x91\xcc\x83',         # ɑ̃
    0x044d: b'\xc9\xaa',                 # ɪ
    0x044e: b'\xc9\x9c\xcb\x90',         # ɜː
    0x044f: b'\xc9\x92',                 # ɒ
    0x0452: b'v',                        # v
    0x0453: b'u\xcb\x90',                # uː
    0x0454: b'\xc9\x94\xcd\x9c\xc3\xb8', # ɔ͜ø
    0x0455: b'\xc7\x90',                 # ǐ
    0x0456: b'j',                        # j
    0x0457: b'\xc9\xa5',                 # ɥ
    0x0458: b'\xc5\x93',                 # œ
    0x045e: b'e',                        # e
    0x0490: b'm',                        # m
    0x0491: b'\xc9\x9b',                 # ɛ
    0x2018: b'\xc9\x91',                 # ɑ
    0x201a: b'\xc9\x94\xcb\x90',         # ɔː
    0x201e: b'\xc9\x99\xcb\x90',         # əː ?
    0x2020: b'\xc9\x99',                 # ə
    0x2021: b'\xc3\xa6',                 # æ
    0x2026: b'\xca\x8c',                 # ʌ
    0x2030: b'\xc3\xb0',                 # ð
    0x2039: b'\xca\xa4',                 # ʤ
    0x20ac: b'\xc9\x94',                 # ɔ
    0x2116: b'a\xcd\x9co',               # a͜o
}.items ()}
# vim: nu ft=python columns=120 :
