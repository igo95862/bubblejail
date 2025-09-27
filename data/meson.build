# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2020 igo95862
install_data(
    'bubblejail-config.png',
    install_dir: get_option('datadir') / 'icons/hicolor/128x128/apps',
    install_tag: 'bubblejail-gui',
)

install_data(
    'bubblejail-config.svg',
    install_dir: get_option('datadir') / 'icons/hicolor/scalable/apps',
    install_tag: 'bubblejail-gui',
)

install_data(
    'bubblejail-config.desktop',
    install_dir: get_option('datadir') / 'applications',
    install_tag: 'bubblejail-gui',
)

install_subdir(
    'usr-share/bubblejail',
    install_dir: get_option('datadir'),
    install_tag: 'runtime',
)

install_emptydir(
    get_option('sysconfdir') / 'bubblejail/profiles',
    install_mode: ['rwxr-xr-x'],
)

install_data(
    'bubblejail_completion.bash',
    install_dir: get_option('datadir') / 'bash-completion/completions',
    rename: 'bubblejail',
    install_tag: 'bash-completion',
)

install_data(
    'bubblejail_completion.fish',
    install_dir: get_option('datadir') / 'fish/vendor_completions.d',
    rename: 'bubblejail.fish',
    install_tag: 'fish-completion',
)
