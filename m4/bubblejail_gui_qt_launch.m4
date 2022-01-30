#!/usr/bin/python3 -IOO
changequote(`$', `$')dnl
ifdef($_PYTHON_PACKAGES_DIR$, $from sys import path


path.append('_PYTHON_PACKAGES_DIR')$)

if __name__ == "__main__":
    from bubblejail.bubblejail_utils import BubblejailSettings

    BubblejailSettings.SHARE_PATH_STR = '_SHARE_PREFIX'

    from bubblejail.bubblejail_gui_qt import run_gui
    run_gui()
