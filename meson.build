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

test_env = environment()
test_env.set('MESON_SOURCE_ROOT', meson.project_source_root())

python_package_env = environment()

templates_dir = meson.current_source_dir() / 'templates'

subdir('src')
subdir('data')
subdir('docs')
subdir('tools')
subdir('test')
