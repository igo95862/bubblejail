#!/usr/bin/python3 -IOO
changequote(`$', `$')dnl
ifdef($_PYTHON_PACKAGES_DIR$, $from sys import path


path.append('_PYTHON_PACKAGES_DIR')$)

if __name__ == "__main__":
    from bubblejail.bubblejail_utils import BubblejailSettings

    BubblejailSettings.HELPER_PATH_STR = \
        '_LIB_PREFIX/bubblejail/bubblejail-helper'
    BubblejailSettings.SHARE_PATH_STR = '_SHARE_PREFIX'
    BubblejailSettings.SYSCONF_PATH_STR = '_SYSCONF_DIR'
    BubblejailSettings.VERSION = '_BUBBLEJAIL_VERSION'

    from bubblejail.bubblejail_cli import bubblejail_main

    bubblejail_main()
