# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2023 igo95862
from __future__ import annotations

from argparse import REMAINDER as ARG_REMAINDER
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, TypedDict

    class CmdMetaDataDict(TypedDict):
        add_argument: dict[str, dict[str, Any]]
        argument: str
        description: "str"


BUBBLEJAIL_CMD: dict[str, CmdMetaDataDict] = {
    "run": {
        "add_argument": {
            "--debug-shell": {
                "action": "store_true",
                "help": (
                    "Opens a shell inside the sandbox instead of "
                    "running program. Useful for debugging."
                ),
            },
            "--dry-run": {
                "action": "store_true",
                "help": (
                    "Prints the bwrap and xdg-desktop-entry arguments "
                    "instead of running."
                ),
            },
            "--debug-helper-script": {
                "type": Path,
                "help": (
                    "Use the specified helper script. "
                    "This is mainly development command."
                ),
                "metavar": "script_path",
            },
            "--debug-log-dbus": {
                "action": "store_true",
                "help": "Enables D-Bus proxy logging.",
            },
            "--wait": {
                "action": "store_true",
                "help": (
                    "Wait on the command inserted in to sandbox " "and get the output."
                ),
            },
            "--debug-bwrap-args": {
                "action": "append",
                "nargs": "+",
                "help": (
                    "Add extra option to bwrap. "
                    "First argument will be prefixed with `--`."
                ),
                "metavar": ("bwrap_option", "bwrap_option_args"),
            },
            "instance_name": {
                "help": "Instance to run.",
            },
            "args_to_instance": {
                "nargs": ARG_REMAINDER,
                "help": "Command and its arguments to run inside instance.",
            },
        },
        "argument": "instance",
        "description": "Launch instance or run command inside.",
    },
    "create": {
        "add_argument": {
            "--profile": {
                "help": "Bubblejail profile to use.",
                "metavar": "profile",
            },
            "--no-desktop-entry": {
                "action": "store_false",
                "help": "Do not create desktop entry.",
            },
            "new_instance_name": {
                "help": "New instance name.",
            },
        },
        "argument": "any",
        "description": "Create new bubblejail instance.",
    },
    "list": {
        "add_argument": {
            "list_what": {
                "choices": (
                    "instances",
                    "profiles",
                    "services",
                ),
                "default": "instances",
                "help": "Type of entity to list.",
            },
        },
        "argument": "any",
        "description": "List certain bubblejail entities.",
    },
    "edit": {
        "add_argument": {
            "instance_name": {
                "help": "Instance to edit config.",
            },
        },
        "argument": "instance",
        "description": "Open instance config in $EDITOR.",
    },
    "generate-desktop-entry": {
        "add_argument": {
            "--profile": {
                "help": "Use desktop entry specified in profile.",
                "metavar": "profile",
            },
            "--desktop-entry": {
                "help": "Desktop entry name or path to use.",
                "metavar": "name_or_path",
            },
            "instance_name": {
                "help": "Instance to generate desktop entry for",
            },
        },
        "argument": "instance",
        "description": "Generate XDG desktop entry for an instance.",
    },
}
