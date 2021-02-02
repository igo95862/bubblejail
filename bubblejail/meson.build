
source_files = [
   '__init__.py',
   'bubblejail_cli.py',
   'bubblejail_directories.py',
   'bubblejail_gui_qt.py',
   'bubblejail_helper.py',
   'bubblejail_instance.py',
   'bubblejail_seccomp.py',
   'bubblejail_utils.py',
   'bwrap_config.py',
   'exceptions.py',
   'services.py',
]

bubblejail_package_dir = get_option('libdir') / 'bubblejail/python_packages/bubblejail'

bubblejail_lib_package = custom_target(
    'bubblejail_lib_package',
    build_by_default : true,
    input : source_files,
    output : source_files + ['__pycache__'],
    install : true,
    install_dir : bubblejail_package_dir,
    command : [bytecode_compiler,
               '--input-files', '@INPUT@',
               '--output-dir', '@OUTDIR@',
               '--lib-prefix', get_option('prefix') / bubblejail_package_dir,
               ],
)
