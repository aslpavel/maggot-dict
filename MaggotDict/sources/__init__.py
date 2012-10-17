# -*- coding: utf-8 -*-
from .dsl import DSLSource
from .dct import DICTSource

__all__ = ('Source', 'DSLSource', 'DICTSource',)
#------------------------------------------------------------------------------#
# Source                                                                       #
#------------------------------------------------------------------------------#
def Source (filename):
    """Create source from filename
    """
    return DSLSource.FromFile (filename) or \
           DICTSource.FromFile (filename) or \
           None

# vim: nu ft=python columns=120 :
