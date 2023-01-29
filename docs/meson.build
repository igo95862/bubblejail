scdoc = find_program(
    'scdoc',
    disabler : true,
)

man_generator = find_program('man_generator.py')

bubblejail_man_page_markdown = custom_target(
    'bubblejail_man_page_markdown',
    depends : bubblejail_lib_package,
    depend_files : files(
        './templates/bubblejail.1.scd.jinja2',
        './man_generator.py',
    ),
    capture : true,
    output : 'bubblejail.1.md',
    command : [
        man_generator,
        '--template-dir', meson.current_source_dir() / 'templates',
    ],
    env : python_package_env,
)

bubblejail_man_page = custom_target(
    'bubblejail_man_page',
    input : bubblejail_man_page_markdown,
    capture : true,
    feed : true,
    build_by_default : true,
    output : 'bubblejail.1',
    install : true,
    install_dir : get_option('mandir') / 'man1',
    command : scdoc,
)
