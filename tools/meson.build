# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2022 igo95862
bubblejail_test_cmd_run = run_target(
    'bubblejail_test_cmd_run',
    command : [py_installation, files('run_test_bubblejail.py'), 'shell'],
    depends : bubblejail_lib_package,
    env : test_env,
)
bubblejail_test_gui_run = run_target(
    'bubblejail_test_gui_run',
    command : [py_installation, files('run_test_bubblejail.py'), 'gui'],
    depends : bubblejail_lib_package,
    env : test_env,
)

lib_prefix_path = get_option('prefix') / get_option('libdir')
share_prefix_path = get_option('prefix') / get_option('datadir')
sysconf_dir_path = '/' / get_option('sysconfdir')

version_display = get_option('version_display')

if version_display == ''
    version_display = meson.project_version()
endif

bytecode_optimization = get_option('bytecode-optimization')
if bytecode_optimization == 0
    python_shebang_short_opts = 'I'
elif bytecode_optimization == 1
    python_shebang_short_opts = 'IO'
elif bytecode_optimization == 2
    python_shebang_short_opts = 'IOO'
else
    error('Unkown python optimization level')
endif

jinja2_compiler = find_program('./jinja2_run.py')

jinja2_commands = [
    jinja2_compiler,
    '--template-dir', templates_dir,
    '--define', 'SHARE_PREFIX', share_prefix_path,
    '--define', 'LIB_PREFIX', lib_prefix_path,
    '--define', 'BUBBLEJAIL_VERSION', version_display,
    '--define', 'SYSCONF_DIR', sysconf_dir_path,
    '--define', 'PYTHON_SHEBANG_SHORT_OPTS', python_shebang_short_opts,
]

if not get_option('use_python_site_packages_dir')
    jinja2_commands += ['--define', 'PYTHON_PACKAGES_DIR', get_option('prefix') / python_packages_dir]
endif

jinja2_commands +=  '@PLAINNAME@'

bubblejail_cli_launch = custom_target(
    'bubblejail_cli_launch',
    build_by_default : true,
    input : files( templates_dir / 'bubblejail_cli_launch.py.jinja2'),
    depend_files : files(
        templates_dir / 'setup_python_path.py.jinja2',
        templates_dir / 'setup_bubblejail_settings.py.jinja2',
    ),
    output : 'bubblejail',
    capture : true,
    install : true,
    install_dir : get_option('bindir'),
    install_mode : 'rwxr-xr-x',
    install_tag : 'runtime',
    command : jinja2_commands,
)

bubblejail_gui_qt_launch = custom_target(
    'bubblejail_gui_qt_launch',
    build_by_default : true,
    input : files( templates_dir / 'bubblejail_gui_qt_launch.py.jinja2'),
    depend_files : files(
        templates_dir / 'setup_python_path.py.jinja2',
        templates_dir / 'setup_bubblejail_settings.py.jinja2',
    ),
    output : 'bubblejail-config',
    capture : true,
    install : true,
    install_dir : get_option('bindir'),
    install_mode : 'rwxr-xr-x',
    install_tag : 'bubblejail-gui',
    command : jinja2_commands,
)

bubblejail_helper_launch = custom_target(
    'bubblejail_helper_launch',
    build_by_default : true,
    input : files( templates_dir / 'bubblejail_helper_launch.py.jinja2'),
    depend_files : files(
        templates_dir / 'setup_python_path.py.jinja2',
        templates_dir / 'setup_bubblejail_settings.py.jinja2',
    ),
    output : 'bubblejail-helper',
    capture : true,
    install : true,
    install_dir : get_option('libdir') / 'bubblejail',
    install_tag : 'runtime',
    install_mode : 'rwxr-xr-x',
    command : jinja2_commands,
)
