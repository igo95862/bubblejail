# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2019-2023 igo95862
from __future__ import annotations

from argparse import ArgumentParser
from shlex import split as shlex_split
from typing import TYPE_CHECKING

from .bubblejail_cli import (
    iter_instance_names,
    iter_list_choices,
    iter_subcommand_options,
    iter_subcommands,
)
from .bubblejail_directories import BubblejailDirectories

if TYPE_CHECKING:
    from collections.abc import Iterable


class AutoCompleteParser:
    def __init__(self) -> None:
        self.last_auto_complete: Iterable[str] = []

    def auto_complete_parser(self, current_cmd: str) -> None:
        words = shlex_split(current_cmd)
        self.last_auto_complete = iter_subcommands()

        if current_cmd[-1].isspace():
            words.append('')

        want_instance_set = {'edit', 'run', 'generate-desktop-entry'}
        base_options = {'--help', '--version'}

        # enumerate words to allow LL parser lookahead
        enumer_words = enumerate(words)
        _ = next(enumer_words)  # cycle 'bubblejail'
        # 1. Parse base options (--help) and subcommands
        while True:
            index, token = next(enumer_words)
            # If its an option autocomplete to base options
            if token.startswith('-'):
                self.last_auto_complete = base_options
                continue
            else:
                # else it is probably a subcommand
                subcommand = token
                break

        try:
            subcommand_options = tuple(iter_subcommand_options(subcommand))
        except KeyError:
            # Check if there are no arguments after this
            try:
                _ = next(enumer_words)
            except StopIteration:
                # If this was the subcommand then give
                # subcommands as completion variants
                return
            else:
                # No auto-completion
                self.last_auto_complete = tuple()

            return

        subject_set = False

        while True:
            index, token = next(enumer_words)

            if subject_set:
                # if we set our subject (i.e. instance)
                # extra arguments should not be completed
                self.last_auto_complete = tuple()
                return

            if token.startswith('-'):
                # Parse base options and subcommands
                self.last_auto_complete = subcommand_options
                continue

            if subcommand == 'list':
                self.last_auto_complete = iter_list_choices()
                subject_set = True
                continue

            if words[index - 1] == '--profile':
                # Wants profile
                self.last_auto_complete = (
                    BubblejailDirectories.iter_profile_names()
                )
                continue

            if subcommand in want_instance_set:
                # Wants instance name
                self.last_auto_complete = iter_instance_names()
                subject_set = True
                continue

            # Does not want anything
            self.last_auto_complete = tuple()

    def auto_complete(self, current_cmd: str) -> Iterable[str]:
        try:
            self.auto_complete_parser(current_cmd)
        except StopIteration:
            ...

        yield from self.last_auto_complete


def run_autocomplete() -> None:
    parser = ArgumentParser()
    parser.add_argument('auto_complete')
    parser.add_argument('current_cmd')
    args = parser.parse_args()

    for x in AutoCompleteParser().auto_complete(args.current_cmd):
        print(x)
