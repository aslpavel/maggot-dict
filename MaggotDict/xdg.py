# -*- codding: utf-8 -*-
import os
try:
    home = os.environ.get ('HOME', '/')

    # user specific
    xdg_data_home = os.environ.get ('XDG_DATA_HOME', os.path.join (home, '.local', 'share'))
    xdg_config_home = os.environ.get ('XDG_CONFIG_HOME', os.path.join (home, '.config'))
    xdg_cache_home = os.environ.get ('XDG_CACHE_HOME', os.path.join (home, '.cache'))

    # global
    xdg_data_dirs = list (filter (bool, os.environ.get ('XDG_DATA_DIRS', '/usr/local/share:/usr/share').split (':')))
    xdg_config_dirs = list (filter (bool, os.environ.get ('XDG_CONFIG_DIRS', '/etc/xdg').split (':')))

finally:
    del home

__all__ = [name for name in globals ().keys () if name.startswith ('xdg_')]
# vim: nu ft=python columns=120 :
