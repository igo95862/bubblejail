# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2022 igo95862
if get_option('generate-namespaces-constants')
    subdir('namespaces_constants')
endif
subdir('bubblejail')

test_env.set('PYTHONPATH', meson.current_build_dir())
python_package_env.set('PYTHONPATH', meson.current_build_dir())
