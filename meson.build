# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2020 igo95862
project('bubblejail',
    version : '0.8.3'
)

fs = import('fs')
pymod = import('python')
py_installation = pymod.find_installation('python3')

bytecode_compiler = find_program(
    'bytecode_compiler.py',
    dirs : [ meson.project_source_root() / 'tools' ],
)

if get_option('use_python_site_packages_dir')
    python_packages_dir = py_installation.get_path('purelib')
else
    python_packages_dir = get_option('libdir') / 'bubblejail/python_packages/'
endif

meson.add_install_script(
    bytecode_compiler,
    '--optimize-level', get_option('bytecode-optimization').to_string(),
    '--packages-dir', python_packages_dir,
    install_tag : 'runtime',
    dry_run : true,
)

python_package_env = environment()
python_package_env.set('MESON_SOURCE_ROOT', meson.project_source_root())

templates_dir = meson.current_source_dir() / 'templates'

subdir('src')
subdir('data')
subdir('docs')
subdir('tools')
subdir('test')
