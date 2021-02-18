lib_prefix_path = get_option('prefix') / get_option('libdir')
share_prefix_path = get_option('prefix') / get_option('datadir')

bubblejail_cli_launch_m4 = custom_target(
    'bubblejail_cli_launch_m4',
    build_by_default : true,
    input : './bubblejail_cli_launch.m4',
    output : 'bubblejail',
    capture : true,
    install : true,
    install_dir : get_option('bindir'),
    install_mode : 'rwxr-xr-x',
    command : [
        m4_compiler,
        '--define', '_LIB_PREFIX=' + lib_prefix_path,
        '--define', '_SHARE_PREFIX=' + share_prefix_path,
        '@INPUT@',
    ]
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
    command : [
        m4_compiler,
        '--define', '_LIB_PREFIX=' + lib_prefix_path,
        '--define', '_SHARE_PREFIX=' + share_prefix_path,
        '@INPUT@',
    ]
)