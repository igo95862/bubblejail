# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2022 igo95862
unittests = files(
    'test_helper.py',
    'test_profiles.py',
    'test_service_info.py',
    'test_auto_completion.py',
    'test_full_run.py',
)

foreach unittest : unittests
    test(
        fs.stem(unittest),
        py_installation,
        args : [unittest],
        env : python_package_env,
    )
endforeach
