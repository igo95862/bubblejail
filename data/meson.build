
install_data(
    'bubblejail-config.png',
    install_dir : get_option('datadir') / 'icons/hicolor/48x48/apps',
)

install_data(
    'bubblejail-config.svg',
    install_dir : get_option('datadir') / 'icons/hicolor/scalable/apps',
)

install_data(
    'bubblejail-config.desktop',
    install_dir : get_option('datadir') / 'applications',
)

install_subdir(
    'bubblejail',
    install_dir : get_option('datadir'),
)

install_data(
    'bubblejail_completion.bash',
    install_dir : get_option('datadir') / 'bash-completion/completions',
    rename : 'bubblejail',
)

install_data(
    'bubblejail_completion.fish',
    install_dir : get_option('datadir') / 'fish/vendor_completions.d',
    rename : 'bubblejail.fish',
)
