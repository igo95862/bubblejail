# SPDX-License-Identifier: GPL-3.0-or-later

# Copyright 2019-2022 igo95862

# This file is part of bubblejail.
# bubblejail is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# bubblejail is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with bubblejail.  If not, see <https://www.gnu.org/licenses/>.


FILE_NAME_SERVICES = 'services.toml'
FILE_NAME_METADATA = 'metadata_v1.toml'


class BubblejailSettings:
    HELPER_PATH_STR: str = '/usr/lib/bubblejail/bubblejail-helper'
    SHARE_PATH_STR: str = '/usr/share'
