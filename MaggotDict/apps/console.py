# -*- coding: utf-8 -*-
import io
import os
import sys
import getopt
import heapq
import itertools

from .app import DictApp
from ..pretzel.console import *
from ..pretzel.log import Log

__all__ = ('ConsoleDictApp',)
#------------------------------------------------------------------------------#
# Console Dictionary Application                                               #
#------------------------------------------------------------------------------#
class ConsoleDictApp (DictApp):
    """Console dictionary application
    """
    comp_default  = 50
    theme_default = {
        'bold'        : Color (COLOR_MAGENTA, COLOR_NONE, ATTR_BOLD | ATTR_FORCE),
        'comment'     : Color (COLOR_BLACK,   COLOR_NONE, ATTR_NONE),
        'example'     : Color (COLOR_DEFAULT, COLOR_NONE, ATTR_FORCE),
        'fold'        : Color (COLOR_BLACK,   COLOR_NONE, ATTR_BOLD),
        'header'      : Color (COLOR_WHITE,   COLOR_BLACK, ATTR_BOLD),
        'italic'      : Color (COLOR_NONE,    COLOR_NONE, ATTR_ITALIC),
        'link'        : Color (COLOR_MAGENTA, COLOR_NONE, ATTR_FORCE),
        'stress'      : Color (COLOR_NONE,    COLOR_NONE, ATTR_UNDERLINE),
        'transcript'  : Color (COLOR_GREEN,   COLOR_NONE, ATTR_BOLD | ATTR_FORCE),
        'translation' : Color (COLOR_WHITE,   COLOR_NONE, ATTR_BOLD),
        'type'        : Color (COLOR_GREEN,   COLOR_NONE, ATTR_FORCE),
        'underline'   : Color (COLOR_NONE,    COLOR_NONE, ATTR_UNDERLINE),
        'words'       : Color (COLOR_WHITE,   COLOR_NONE, ATTR_BOLD),
    }

    def __init__ (self):
        DictApp.__init__ (self)

        if sys.stdout.isatty ():
            self.console = Console (io.open (sys.stdout.fileno (), 'wb', closefd = False))
            self.dispose += self.console
        else:
            self.console = PlainConsole ()

        self.theme = self.theme_default

    #--------------------------------------------------------------------------#
    # Usage                                                                    #
    #--------------------------------------------------------------------------#
    def Usage (self):
        """Print usage message
        """
        sys.stderr.write ('''Usage: {} [options] <word>
options:
    -I <file> : install dictionary
    -U <name> : uninstall dictionary
    -d <name> : disable dictionary
    -s        : show statistics
    -h|?      : show this help message
'''.format (os.path.basename (sys.argv [0])))
        sys.stderr.flush ()

    #--------------------------------------------------------------------------#
    # Execute                                                                  #
    #--------------------------------------------------------------------------#
    def Execute (self):
        """Execute application
        """
        # bash completion
        comp_line, comp_point = os.environ.get ('COMP_LINE'), os.environ.get ('COMP_POINT')
        if comp_line and comp_point:
            self.Completion (comp_line, int (comp_point))
            return

        # parse arguments
        try:
            opts, args = getopt.getopt (sys.argv [1:], "?hsI:U:d:")

        except getopt.GetoptError as error:
            Log.Error (str (error))
            self.Usage ()
            return

        for opt, arg in opts:
            # Statistics
            if opt == '-s':
                for name in self.Dicts:
                    print (name)
                return

            # Install
            elif opt == '-I':
                try:
                    with Log ('installing {}'.format (os.path.basename (arg))) as report:
                        self.Install (arg, report)

                except Exception:
                    self.Usage ()

                return

            # Uninstall
            elif opt == '-U':
                try:
                    self.Uninstall (arg)

                except Exception:
                    Log.Error (error)
                    self.Usage ()

                return

            # Help
            elif opt in ('-h', '-?'):
                self.Usage ()
                return

            else:
                Log.Warning ('Option {} has not been implemented yet'.format (opt))
                return

        word = ' '.join (args)
        if not word:
            Log.Error ('Word is required')
            self.Usage ()
            return

        for name, dct in self.Dicts.items ():
            card_word, card = dct.ByWord [word]
            if card:
                text = Text ()
                self.Render (card, name = name, text = text)
                self.console.Write (text)

    #--------------------------------------------------------------------------#
    # Render                                                                   #
    #--------------------------------------------------------------------------#
    def RenderScope (self, name, value, ctx):
        """Render scope
        """
        text = ctx ['text']

        if name == 'card':
            text.Write (ctx ['name'].center (self.console.Size () [1]), self.theme.get ('header'))
            text.Write ('\n ')
            text.Write (', '.join (value ['words']), self.theme.get ('words'))
            text.Write ('\n\n')

            yield True
            text.Write ('\n')
            return

        elif name == 'indent':
            text.Write (' ' + '  ' * value)
            yield True

            text.Write ('\n')
            return

        elif name == 'text':
            text.Write (value)

        elif name == 'transcript':
            text.Write (value, self.theme.get (name))

        elif name == 'color':
            pass

        elif name == 'root':
            pass

        elif name in self.theme:
            with text.Color (self.theme [name]):
                yield True
                return

        else:
            text.Write ('<{}:{}>'.format (name, value))
            yield True

            text.Write ('</{}>'.format (name))
            return

        yield True

    #--------------------------------------------------------------------------#
    # Completion                                                               #
    #--------------------------------------------------------------------------#
    def Completion (self, comp_line, comp_point):
        """Bash completion
        """
        name, sep, complete = comp_line [:comp_point].partition (' ')
        complete = complete.encode ('utf-8')

        words = list (
            itertools.islice (
                itertools.takewhile (lambda word: word.startswith (complete), (word for word, _ in
                    heapq.merge (*(dct.word_index.index [complete:] for dct in self.Dicts.values ())))),
                self.comp_default))

        if words:
            word_size = os.path.commonprefix (words).rfind (b' ') + 1
            for word in words:
                print (word [word_size:].decode ('utf-8'))

#------------------------------------------------------------------------------#
# Plain Console                                                                #
#------------------------------------------------------------------------------#
class PlainConsole (object):
    """Minimal plain console for non tty output
    """

    def Write (self, text):
        sys.stdout.write (text.Encode ().decode ('utf-8'))
        sys.stdout.flush ()

    def Size (self):
        return 0, 0

# vim: nu ft=python columns=120 :
