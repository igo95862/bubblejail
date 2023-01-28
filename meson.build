project('bubblejail',
    version : '0.6.2'
)

fs = import('fs')
pymod = import('python')
py_installation = pymod.find_installation('python3')

bytecode_compiler = find_program(
    'bytecode_compiler.py',
    dirs : [ meson.project_source_root() / 'tools' ],
)
m4_compiler = find_program('m4')

test_env = environment()
test_env.set('MESON_SOURCE_ROOT', meson.project_source_root())

subdir('src')
subdir('m4')
subdir('data')
subdir('docs')
subdir('tools')
subdir('test')
