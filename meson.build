project('bubblejail')

pymod = import('python')
py_installation = pymod.find_installation('python3')

subdir(meson.project_name())
subdir('data')

meson.add_install_script('meson_complile_bytecode.build')

test('unittest', py_installation,
    args : ['-m', 'unittest'],
    workdir : meson.source_root(),
)