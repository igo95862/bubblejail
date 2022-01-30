#!/usr/bin/python3 -IOO
changequote(`$', `$')dnl
ifdef($_PYTHON_PACKAGES_DIR$, $from sys import path


path.append('_PYTHON_PACKAGES_DIR')$)

if __name__ == "__main__":
    from bubblejail.bubblejail_helper import bubblejail_helper_main
    bubblejail_helper_main()
