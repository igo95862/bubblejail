#!/usr/bin/python3 -IOO

from sys import path


path.append('_LIB_PREFIX/bubblejail/python_packages')

if __name__ == "__main__":
    from bubblejail.bubblejail_utils import BubblejailSettings

    BubblejailSettings.HELPER_PATH_STR = \
        '_LIB_PREFIX/bubblejail/bubblejail-helper'
    BubblejailSettings.SHARE_PATH_STR = '_SHARE_PREFIX'

    from bubblejail.bubblejail_cli import bubblejail_main

    bubblejail_main()
