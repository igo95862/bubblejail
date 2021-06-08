gtk_dependency = dependency('gtk+-3.0')

add_languages('c', required: true)

config_sources = files(
    'main.c', 'bubblejail_config.h',
    'instance_list.c'
)

demo = executable('gtk_test', config_sources,
    build_by_default: false,
    dependencies: gtk_dependency,
    c_args: [
        '-Wall', '-Wextra',
        '-Wconversion',
    ])

run_target('gtk-demo', command: demo)
