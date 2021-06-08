gtk_dependency = dependency('gtk+-3.0')

add_languages('c', required: true)

demo = executable('gtk_test', 'main.c',
    build_by_default: false,
    dependencies: gtk_dependency,
    c_args: [
        '-Wall', '-Wextra',
        '-Wconversion',
    ])

run_target('gtk-demo', command: demo)
