# -*- coding: utf-8 -*-
import os
import uuid

from .xdg import xdg_data_home
from .sources import Source
from .dictionary import Dictionary

from .pretzel.store import FileStore
from .pretzel.async import Core, Async
from .pretzel.remoting import ForkDomain

__all__ = ('Application',)
#------------------------------------------------------------------------------#
# Slovar
#------------------------------------------------------------------------------#
class SlovarError (Exception): pass
class Slovar (object):
    root_path  = os.path.join (xdg_data_home, 'maggot-dict')
    dict_path  = os.path.join (root_path, 'dicts')
    store_path = os.path.join (root_path, 'state.store')

    def __init__ (self, core = None):
        self.core = core or Core.Instance ()

        # check paths
        if not os.path.isdir (self.dict_path):
            os.makedirs (self.dict_path)

        # store
        self.store = FileStore (self.store_path, 'c')

        # dictionaries
        self.dcts = {}
        for name in os.listdir (self.dict_path):
            if name.endswith ('.mdict'):
                dct = Dictionary (os.path.join (self.dict_path, name))
                self.dcts [dct.Name] = dct
            elif name.endswith ('.tmp'):
                os.unlink (os.path.join (self.dict_path, name))

    #--------------------------------------------------------------------------#
    # Install | Uninstall                                                      #
    #--------------------------------------------------------------------------#
    @Async
    def InstallAsync (self, filename, report = None):
        with ForkDomain () as domain:
            yield domain.Connect ()
            dct_path = ((yield domain.Call (SlovarInstall, filename, domain.ToProxy (report)))
                if report else (yield domain.Call (SlovarInstall, filename)))

        dct = Dictionary (dct_path)
        self.dcts [dct.Name] = dct

    def Install (self, filename, report = None):
        dct = Dictionary (SlovarInstall (filename, report))
        self.dcts [dct.Name] = dct

    '''
    def Install (self, filename, name = None):
        source = Source (filename)
        if source is None:
            raise SlovarError ('Unsupported file type: {}'.format (filename))

        dct_filename = os.path.join (self.dict_path, (name or source.Name) + '.mdict')
        if os.path.isfile (dct_filename):
            raise SlovarError ('Dictionary exists: {}', name or source.Name)
        dct = Dictionary.FromSource (source, dct_filename)

        self.dcts [dct.Name] = dct
    '''

    def Uninstall (self, name):
        dct = self.dcts.pop (name, None)
        if dct is None:
            raise SlovarError ('No such dictionary: {}'.format (name))
        dct.Dispose ()
        os.unlink (dct.File)

    #--------------------------------------------------------------------------#
    # Lookup                                                                   #
    #--------------------------------------------------------------------------#
    def Cards (self, word, card_default = None):
        items = []
        for dct in self.dcts.values ():
            card = dct.Card (word)
            if card is None:
                continue
            items.append (card)

        return items or card_default

    #--------------------------------------------------------------------------#
    # Disposable                                                               #
    #--------------------------------------------------------------------------#
    def Dispose (self):
        self.store.Dispose ()

    def __enter__ (self):
        return self

    def __exit__ (self, et, eo, tb):
        self.Dispose ()
        return False

#------------------------------------------------------------------------------#
# Helpers                                                                      #
#------------------------------------------------------------------------------#
def SlovarInstall (filename, report = None):
    """Install dictionary from file name
    """
    if report:
        value_next = [0]
        def report_reduced (value):
            if value * 100 >= value_next [0]:
                value_next [0] += 1
                report (value)
    else:
        report_reduced = None

    try:
        tmp_path = os.path.join (Slovar.dict_path, '{}.tmp'.format (uuid.uuid4 ()))
        dct = Dictionary.Compile (filename, tmp_path, report_reduced)
        dct_path = os.path.join (Slovar.dict_path, '{}.mdict'.format (dct.Name))
        os.rename (tmp_path, dct_path)
    finally:
        if os.path.exists (tmp_path):
            os.unlink (tmp_path)

    return dct_path

# vim: nu ft=python columns=120 :
