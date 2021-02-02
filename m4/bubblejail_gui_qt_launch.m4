#!/usr/bin/python3 -IOO

from sys import path


path.append('_LIB_PREFIX/bubblejail/python_packages')

if __name__ == "__main__":
    from bubblejail.bubblejail_utils import BubblejailSettings

    BubblejailSettings.SHARE_PATH_STR = '_SHARE_PREFIX'

    from bubblejail.bubblejail_gui_qt import run_gui
    run_gui()
