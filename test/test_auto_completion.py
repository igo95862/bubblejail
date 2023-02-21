# SPDX-License-Identifier: GPL-3.0-or-later

# Copyright 2023 igo95862

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
from __future__ import annotations

from unittest import TestCase, main

from bubblejail.bubblejail_cli import iter_list_choices
from bubblejail.bubblejail_cli_autocomplete import AutoCompleteParser
from bubblejail.bubblejail_cli_metadata import BUBBLEJAIL_CMD


class TestAutocomplete(TestCase):
    def setUp(self) -> None:
        self.parser = AutoCompleteParser()

    def test_second_arg(self) -> None:
        self.assertEqual(
            tuple(self.parser.auto_complete('bubblejail ')),
            tuple(BUBBLEJAIL_CMD.keys())
        )

        self.assertEqual(
            tuple(self.parser.auto_complete('bubblejail lis')),
            tuple(BUBBLEJAIL_CMD.keys())
        )

        self.assertEqual(
            tuple(self.parser.auto_complete('bubblejail asd ')),
            tuple(),
        )

    def test_subcommand(self) -> None:
        self.assertEqual(
            tuple(self.parser.auto_complete('bubblejail list ')),
            tuple(iter_list_choices()),
        )


if __name__ == '__main__':
    main()
