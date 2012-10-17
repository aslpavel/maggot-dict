#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Description: converts makedicts (https://xdxf.svn.sourceforge.net/svnroot/xdxf/trunk)
#   to python transliteration table
from __future__ import print_function
import sys
import re
import io
import os

def main ():
    if len (sys.argv) < 2:
        sys.stderr.write ('Usage: {} <dsl_ipa.cpp>\n'.format (os.path.basename (sys.argv [0])))
        sys.exit (1)
    dsl_ipa_file = sys.argv [1]

    if sys.version_info [0] < 3:
        sys.stderr.write (':: error: python version >= 3 is required\n')
        sys.exit (1)

    map_pattern = re.compile (r'^\s*ipa_to_unicode_make_pair\(0x([^,]*),\s*([^)]*)\), // (.*$)')
    table = []

    try:
        with open (dsl_ipa_file) as stream:
            for line in stream:
                match = map_pattern.match (line)  
                if match:
                    code, values, comment = match.groups ()
                    # code
                    code = int (code, 16)

                    # values
                    string = io.StringIO ()
                    for value in list (map (lambda code: int (code [2:], 16), values.split (', '))):
                        string.write (chr (value))

                    # table
                    table.append ((code, string.getvalue ().encode ('utf-8'), comment))
    except IOError as error:
        sys.stderr.write (':: error: {}: {}\n'.format (error.strerror, dsl_ipa_file))
        sys.exit (1)
        

    print ('transcription_map = {')
    for code, values, comment in table:
        print ('    0x{:0>4x}: {:<28} # {}'.format (code, '{},'.format (values), comment))
    print ('}')

if __name__ == '__main__':
    main ()
# vim: nu ft=python columns=120 :
