# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2019-2022 igo95862
from __future__ import annotations

FILE_NAME_SERVICES = "services.toml"
FILE_NAME_METADATA = "metadata_v1.toml"


class BubblejailSettings:
    HELPER_PATH_STR: str = "/usr/lib/bubblejail/bubblejail-helper"
    SHARE_PATH_STR: str = "/usr/share"
    SYSCONF_PATH_STR: str = "/etc"
    VERSION: str = "UNDEFINED"
