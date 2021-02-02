#!/usr/bin/python3 -IOO

from sys import path


path.append('_LIB_PREFIX/bubblejail/python_packages')

if __name__ == "__main__":
    from bubblejail.bubblejail_helper import bubblejail_helper_main
    bubblejail_helper_main()
