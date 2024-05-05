# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2021 igo95862
scdoc = find_program(
    'scdoc',
    disabler : true,
    required : false,
)

man_generator = find_program('man_generator.py')

bubblejail_man_page_markdown = custom_target(
    'bubblejail_man_page_markdown',
    depend_files : files(
        './templates/bubblejail.1.scd.jinja2',
        './man_generator.py',
    ),
    capture : true,
    output : 'bubblejail.1.md',
    command : [
        man_generator,
        '--template-dir', meson.current_source_dir() / 'templates',
        'cmd',
    ],
    env : python_package_env,
)

bubblejail_man_page = custom_target(
    'bubblejail_man_page',
    input : bubblejail_man_page_markdown,
    capture : true,
    feed : true,
    output : 'bubblejail.1',
    install : get_option('man'),
    install_dir : get_option('mandir') / 'man1',
    command : scdoc,
    install_tag : 'man'
)

bubblejail_services_man_page_markdown = custom_target(
    'bubblejail_services_man_page_markdown',
    depend_files : files(
        './templates/bubblejail.services.5.scd.jinja2',
        './man_generator.py',
    ),
    capture : true,
    output : 'bubblejail.services.5.md',
    command : [
        man_generator,
        '--template-dir', meson.current_source_dir() / 'templates',
        'services',
    ],
    env : python_package_env,
)

bubblejail_services_man_page = custom_target(
    'bubblejail_services_man_page',
    input : bubblejail_services_man_page_markdown,
    capture : true,
    feed : true,
    output : 'bubblejail.services.5',
    install : get_option('man'),
    install_dir : get_option('mandir') / 'man5',
    command : scdoc,
    install_tag : 'man'
)
