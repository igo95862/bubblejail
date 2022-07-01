lib_prefix_path = get_option('prefix') / get_option('libdir')
share_prefix_path = get_option('prefix') / get_option('datadir')
sysconf_dir_path = get_option('sysconfdir')

version_display = get_option('version_display')

if version_display == ''
    version_display = meson.project_version()
endif

m4_commands = [
    m4_compiler,
    '--define', '_SHARE_PREFIX=' + share_prefix_path,
    '--define', '_LIB_PREFIX=' + lib_prefix_path,
    '--define', '_BUBBLEJAIL_VERSION=' + version_display,
    '--define', '_SYSCONF_DIR=' + sysconf_dir_path,
]

if not get_option('use_python_site_packages_dir')
    m4_commands += ['--define', '_PYTHON_PACKAGES_DIR=' + get_option('prefix') / python_packages_dir]
endif

m4_commands +=  '@INPUT@'

bubblejail_cli_launch_m4 = custom_target(
    'bubblejail_cli_launch_m4',
    build_by_default : true,
    input : './bubblejail_cli_launch.m4',
    output : 'bubblejail',
    capture : true,
    install : true,
    install_dir : get_option('bindir'),
    install_mode : 'rwxr-xr-x',
    command : m4_commands,
)

bubblejail_gui_qt_launch_m4 = custom_target(
    'bubblejail_gui_qt_launch_m4',
    build_by_default : true,
    input : './bubblejail_gui_qt_launch.m4',
    output : 'bubblejail-config',
    capture : true,
    install : true,
    install_dir : get_option('bindir'),
    install_mode : 'rwxr-xr-x',
    command : m4_commands,
)

bubblejail_helper_launch_m4 = custom_target(
    'bubblejail_helper_launch_m4',
    build_by_default : true,
    input : './bubblejail_helper_launch.m4',
    output : 'bubblejail-helper',
    capture : true,
    install : true,
    install_dir : get_option('libdir') / 'bubblejail',
    install_mode : 'rwxr-xr-x',
    command : m4_commands,
)
