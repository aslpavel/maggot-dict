# -*- coding: utf-8 -*-

__all__ = []
#------------------------------------------------------------------------------#
# Load Test Protocol                                                           #
#------------------------------------------------------------------------------#
def load_tests (loader, tests, pattern):
    """Laod test protocol
    """
    from unittest import TestSuite
    from . import pretzel

    suite = TestSuite ()
    for test in (pretzel,):
        suite.addTests (loader.loadTestsFromModule (test))

    return suite

# vim: nu ft=python columns=120 :
