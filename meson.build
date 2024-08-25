# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2020 igo95862
project('bubblejail',
    version : '0.9.1',
    # Patch out these lines to install bubblejail's packages to site-packages
    default_options : {
        'python.purelibdir' : 'lib/bubblejail/python-packages',
        'python.platlibdir' : 'lib/bubblejail/python-packages',
    },
)

fs = import('fs')
pymod = import('python')
py_installation = pymod.find_installation('python3')
python_purelib_option = get_option('python.purelibdir')

if python_purelib_option == py_installation.get_path('purelib') or python_purelib_option == ''
    extra_python_packages_dir = ''
else
    extra_python_packages_dir = get_option('prefix') / python_purelib_option
    message('Using non site-packages directory', extra_python_packages_dir)
endif

if get_option('use-vendored-python-lxns').enabled()
    subproject('python-lxns', default_options : {'use_limited_api': true})
endif

python_package_env = environment()
python_package_env.set('MESON_SOURCE_ROOT', meson.project_source_root())

templates_dir = meson.current_source_dir() / 'templates'

subdir('src')
subdir('data')
subdir('docs')
subdir('tools')
subdir('test')
