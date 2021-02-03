sphinx_build = find_program('sphinx-build')

man_sources = files('./man/bubblejail.rst', './man/conf.py')

bubblejail_man_page = custom_target(
    'bubblejail_man_page',
    input : man_sources,
    build_by_default : true,
    output : 'bubblejail.1',
    install : true,
    install_dir : get_option('mandir') / 'man1',
    command : [
        sphinx_build,
        '-b', 'man',
        meson.current_source_dir() / 'man', '@OUTDIR@',
    ]
)
