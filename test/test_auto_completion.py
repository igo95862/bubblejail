# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2023 igo95862
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
            tuple(self.parser.auto_complete("bubblejail ")),
            tuple(BUBBLEJAIL_CMD.keys()),
        )

        self.assertEqual(
            tuple(self.parser.auto_complete("bubblejail lis")),
            tuple(BUBBLEJAIL_CMD.keys()),
        )

        self.assertEqual(
            tuple(self.parser.auto_complete("bubblejail asd ")),
            tuple(),
        )

    def test_subcommand(self) -> None:
        self.assertEqual(
            tuple(self.parser.auto_complete("bubblejail list ")),
            tuple(iter_list_choices()),
        )


if __name__ == "__main__":
    main()
