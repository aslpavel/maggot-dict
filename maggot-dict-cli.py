#! /usr/bin/env python
# -*- coding: utf-8 -*-
from MaggotDict.pretzel.log import Log
from MaggotDict.pretzel.app import Application
from MaggotDict.apps.console import ConsoleDictApp

#------------------------------------------------------------------------------#
# Main                                                                         #
#------------------------------------------------------------------------------#
@Application (name = 'cli')
def Main (app):
    with ConsoleDictApp () as capp:
        capp ()

if __name__ == '__main__':
    Main ()

# vim: nu ft=python columns=120 :
