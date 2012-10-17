# -*- coding: utf-8 -*-
import os
import uuid

from ..xdg import xdg_data_home
from ..dictionary import Dictionary

from ..pretzel.store import FileStore
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

    dct_suffix = '.mdict'

    def __init__ (self):
        self.dispose = CompositeDisposable ()

        # check paths
        if not os.path.isdir (self.dcts_path):
            os.makedirs (self.dcts_path)

        # state
        self.state = FileStore (self.state_path, 'c')
        self.dispose += self.state

        # dictionaries
        self.dcts = {}
        for name in os.listdir (self.dcts_path):
            if name.endswith (self.dct_suffix):
                dct = Dictionary (os.path.join (self.dcts_path, name))
                self.dispose += dct
                self.dcts [dct.Name] = dct

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
    # Properties                                                               #
    #--------------------------------------------------------------------------#
    @property
    def Dicts (self):
        """Available dictionaries
        """
        return self.dcts

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

            self.dcts [dct.Name] = dct
            self.dispose += dct

        finally:
            if os.path.exists (tmp_path):
                os.unlink (tmp_path)

    def Uninstall (self, name):
        """Remove dictionary
        """
        dct = self.dcts.pop (name, None)
        if dct is None:
            raise DictAppError ('No such dictionary: {}'.format (name))

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


# vim: nu ft=python columns=120 :