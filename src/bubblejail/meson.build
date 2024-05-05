# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2020 igo95862
source_files = [
   '__init__.py',
   'bubblejail_cli.py',
   'bubblejail_cli_metadata.py',
   'bubblejail_cli_autocomplete.py',
   'bubblejail_directories.py',
   'bubblejail_gui_qt.py',
   'bubblejail_helper.py',
   'bubblejail_instance.py',
   'bubblejail_runner.py',
   'bubblejail_seccomp.py',
   'bubblejail_utils.py',
   'bwrap_config.py',
   'exceptions.py',
   'services.py',
   'py.typed',
   'namespaces.py',
   'namespaces_constants.py',
]



bubblejail_package_dir = python_packages_dir / 'bubblejail'

install_data(
    source_files,
    install_dir : bubblejail_package_dir,
    install_tag : 'runtime',
)
