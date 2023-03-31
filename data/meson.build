
install_data(
    'bubblejail-config.png',
    install_dir : get_option('datadir') / 'icons/hicolor/48x48/apps',
    install_tag : 'bubblejail-gui',
)

install_data(
    'bubblejail-config.svg',
    install_dir : get_option('datadir') / 'icons/hicolor/scalable/apps',
    install_tag : 'bubblejail-gui',
)

install_data(
    'bubblejail-config.desktop',
    install_dir : get_option('datadir') / 'applications',
    install_tag : 'bubblejail-gui',
)

install_subdir(
    'usr-share/bubblejail',
    install_dir : get_option('datadir'),
    install_tag : 'runtime'
)

install_subdir(
    'etc/bubblejail',
    install_dir : get_option('sysconfdir'),
    exclude_files : ['profiles/.gitkeep'],
    install_tag : 'runtime'
)

install_data(
    'bubblejail_completion.bash',
    install_dir : get_option('datadir') / 'bash-completion/completions',
    rename : 'bubblejail',
    install_tag : 'bash-completion',
)

install_data(
    'bubblejail_completion.fish',
    install_dir : get_option('datadir') / 'fish/vendor_completions.d',
    rename : 'bubblejail.fish',
    install_tag : 'fish-completion',
)
