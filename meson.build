project('bubblejail',
    version : '0.5.3'
)

pymod = import('python')
py_installation = pymod.find_installation('python3')

bytecode_compiler = find_program('bytecode_compiler.build')
m4_compiler = find_program('m4')

subdir(meson.project_name())
subdir('m4')
subdir('data')
subdir('docs')

test('unittest', py_installation,
    args : ['-m', 'unittest'],
    workdir : meson.source_root(),
)
