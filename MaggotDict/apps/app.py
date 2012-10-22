# -*- coding: utf-8 -*-
import os
import uuid

from ..xdg import xdg_data_home
from ..dictionary import Dictionary

from ..pretzel.store import FileStore
from ..pretzel.config import StoreConfig
from ..pretzel.disposable import CompositeDisposable

__all__ = ('DictApp', 'DictAppError',)
#------------------------------------------------------------------------------#
# Dictionary Application                                                       #
#------------------------------------------------------------------------------#
class DictAppError (Exception):
    """Dictionary application error
    """
    pass

class DictApp (object):
    """Dictionary application
    """
    root_path  = os.path.join (xdg_data_home, 'maggot-dict')
    dcts_path  = os.path.join (root_path, 'dicts')
    state_path = os.path.join (root_path, 'state.store')

    dct_suffix  = '.mdict'
    config_name = b'mdict::config'

    def __init__ (self):
        self.dispose = CompositeDisposable ()

        # check paths
        if not os.path.isdir (self.dcts_path):
            os.makedirs (self.dcts_path)

        # state
        self.state = FileStore (self.state_path, 'c')
        self.dispose += self.state

        # configuration
        self.config = StoreConfig (self.state, self.config_name, lambda: {
            'dcts': {},
        })
        self.dispose += self.config

        # history
        self.hist = History (self.state)

        # dictionaries
        dcts = []
        for name in os.listdir (self.dcts_path):
            if name.endswith (self.dct_suffix):
                dct = Dictionary (os.path.join (self.dcts_path, name))
                self.dispose += dct

                # configuration
                dct_config = self.config.dcts.Get (dct.Name, None)
                if dct_config is None:
                    self.config.dcts [dct.Name] = {
                        'weight': 0,
                        'disabled': False
                    }
                    dct_config = self.config.dcts [dct.Name]

                dct.config = dct_config
                dcts.append (dct)

        self.dcts = Dicts (dcts)

    #--------------------------------------------------------------------------#
    # Properties                                                               #
    #--------------------------------------------------------------------------#
    @property
    def Dicts (self):
        """Dictionaries
        """
        return self.dcts

    @property
    def History (self):
        """History
        """
        return self.hist

    #--------------------------------------------------------------------------#
    # Execute                                                                  #
    #--------------------------------------------------------------------------#
    def __call__ (self):
        """Execute application
        """
        self.Execute ()

    def Execute (self):
        """Execute application
        """
        pass

    #--------------------------------------------------------------------------#
    # Render                                                                   #
    #--------------------------------------------------------------------------#
    def Render (self, card, **ctx):
        """Render card
        """
        body = card ['body']

        def render (node):
            name = node ['name']
            value = node.get ('value', None)
            children = node.get ('children', None)

            scope = self.RenderScope (name, value, ctx)
            try:
                if scope.send (None) and children:
                    for child in children:
                        render (child)
                scope.send (None)

            except StopIteration: pass
            finally:
                scope.close ()

        scope = self.RenderScope ('card', card, ctx)
        try:
            if scope.send (None):
                render (body)
            scope.send (None)

        except StopIteration: pass
        finally:
            scope.close ()

    def RenderScope (self, name, value, ctx):
        """Render scope
        """
        yield True

    #--------------------------------------------------------------------------#
    # Install | Uninstall                                                      #
    #--------------------------------------------------------------------------#
    def Install (self, path, report = None):
        """Install dictionary
        """
        try:
            tmp_path = os.path.join (self.dcts_path, '{}.tmp'.format (uuid.uuid4 ()))
            dct = Dictionary.Compile (path, tmp_path, report)
            dct_path = os.path.join (self.dcts_path, '{}{}'.format (dct.Name, self.dct_suffix))
            os.rename (tmp_path, dct_path)

            self.config.dcts [dct.Name] = {
                'weight': 0,
                'disabled': False
            }
            dct.config = self.config.dcts [dct.Name]

            self.dcts.Add (dct)
            self.dispose += dct

        finally:
            if os.path.exists (tmp_path):
                os.unlink (tmp_path)

    def Uninstall (self, id):
        """Remove dictionary
        """
        dct = self.dcts.Pop (id)
        if dct is None:
            raise DictAppError ('No such dictionary: {}'.format (id))

        del self.config.dcts [dct.Name]
        dct.Dispose ()
        os.unlink (dct.File)

    #--------------------------------------------------------------------------#
    # Dispose                                                                  #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        """Dispose object
        """
        self.dispose.Dispose ()

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

#------------------------------------------------------------------------------#
# Dictionaries set                                                             #
#------------------------------------------------------------------------------#
class Dicts (object):
    """Dictionaries set
    """
    by_index_key = lambda self, dct: (-dct.config.weight, dct.Name)

    def __init__ (self, dcts):
        self.by_index = sorted (dcts, key = self.by_index_key)
        self.by_name = dict ((dct.Name, dct) for dct in self.by_index)

    def __iter__ (self):
        return iter (self.by_index)

    def __getitem__ (self, id):
        """Get dictionary by id
        """
        try:
            index = int (id)
            if 0 <= index < len (self.by_index):
                return self.by_index [index]
        except ValueError: pass
        return self.by_name.get (id)

    def Pop (self, id, default = None):
        dct = self [id]
        if dct is None:
            return default

        self.by_index.remove (dct)
        self.by_name.pop (dct.Name)

        return dct

    def Add (self, dct):
        self.by_index.append (dct)
        self.by_index.sort (key = self.by_index_key)
        self.by_name [dct.Name] = dct

    def __len__ (self):
        return len (self.by_index)

    def Enabled (self):
        return iter (dct for dct in self.by_index if not dct.config.disabled)

#------------------------------------------------------------------------------#
# History                                                                      #
#------------------------------------------------------------------------------#
class History (object):
    """Lookup history
    """
    by_word_name = b'mdict::hist_word'
    by_count_name = b'mdict::hist_count'

    def __init__ (self, store):
        self.by_word = store.Mapping (self.by_word_name, key_type = 'json', value_type = 'struct:>Q')
        self.by_count = store.Mapping (self.by_count_name, key_type = 'json', value_type = 'struct:b')

    def WordAdd (self, word):
        count = self.by_word.get (word, 0)
        self.by_word [word] = count + 1

        self.by_count.pop ([-count, word])
        self.by_count [[-count - 1, word]] = 0

    def WordGet (self, word):
        return self.by_word.get (word, 0)

    def __iter__ (self):
        return ((word, -count) for count, word in self.by_count)

# vim: nu ft=python columns=120 :