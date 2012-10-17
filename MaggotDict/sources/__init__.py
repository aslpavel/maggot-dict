# -*- coding: utf-8 -*-
from .dsl import DSLSource

__all__ = ('Source', 'DSLSource',)
#------------------------------------------------------------------------------#
# Source                                                                       #
#------------------------------------------------------------------------------#
def Source (filename):
    """Create source from filename
    """
    source = DSLSource.FromFile (filename)
    if source:
        return source

# vim: nu ft=python columns=120 :
