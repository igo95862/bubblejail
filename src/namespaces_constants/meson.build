
add_languages('c')

lint_args = ['-Wall', '-Wextra', '-Werror']

namespaces_constants_json_printer = executable(
    'namespaces_constants_json_printer',
    'namespaces_constants_json.c',
    c_args : lint_args,
)

namespaces_constants_json = custom_target(
    'namespaces_constants_json',
    output : 'namespaces_constants.json',
    install : false,
    command : [namespaces_constants_json_printer],
    capture : true,
)

run_target(
    'print_namespaces_constants_json',
    command : [namespaces_constants_json_printer],
)

namespaces_constants_generator = find_program('./generate_namespaces_constants.py')


namespaces_constants_module = custom_target(
    'namespaces_constants_module',
    build_by_default : true,
    install : false,
    depend_files : files(
        './namespaces_constants_json.c',
        templates_dir / 'namespaces_constants.py.jinja2',
    ),
    output : 'namespaces_constants.py',
    capture : true,
    command : [
        namespaces_constants_generator,
        '--template-dir', templates_dir,
        namespaces_constants_json,
    ],
)
