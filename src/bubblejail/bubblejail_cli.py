# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2019-2023 igo95862
from __future__ import annotations

from argparse import ArgumentParser
from asyncio import run as async_run
from os import environ, isatty, stat
from pathlib import Path
from sys import argv, stderr, stdout
from typing import TYPE_CHECKING

from .bubblejail_cli_metadata import BUBBLEJAIL_CMD
from .bubblejail_directories import BubblejailDirectories
from .bubblejail_utils import BubblejailSettings
from .dbus_proxy import DBusLogEnum
from .services import SERVICES_CLASSES

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Iterable, Iterator

    from .bubblejail_instance import BubblejailInstance


def iter_instance_names() -> Generator[str, None, None]:
    for instance_directory in BubblejailDirectories.iter_instances_path():
        yield instance_directory.name


def iter_subcommands() -> Generator[str, None, None]:
    yield from BUBBLEJAIL_CMD.keys()


def iter_subcommand_options(
    subcommand_text: str,
) -> Generator[str, None, None]:
    yield from (
        x for x in BUBBLEJAIL_CMD[subcommand_text]["add_argument"] if x.startswith("--")
    )


def iter_list_choices() -> Iterable[str]:
    yield from BUBBLEJAIL_CMD["list"]["add_argument"]["list_what"]["choices"]


def _extra_args_converter(command_sequence: list[str]) -> Generator[str, None, None]:
    command_iter = iter(command_sequence)

    try:
        argword = next(command_iter)
    except StopIteration:
        raise ValueError("Expected at least one argument")

    yield f"--{argword}"

    yield from command_iter


def run_running_instance(
    instance: BubblejailInstance,
    args_to_instance: list[str],
    wait: bool,
    dry_run: bool,
) -> None:
    if dry_run:
        print("Found helper socket.", file=stderr)
        print("Args would be be sent: ", args_to_instance, file=stderr)
        return
    else:
        print("Instance already running.", file=stderr)
        print(
            "Sending command to the instance: ",
            args_to_instance,
            file=stderr,
        )

    command_return_text = async_run(
        instance.send_run_rpc(
            args_to_run=args_to_instance,
            wait_for_response=wait,
        )
    )
    if wait and command_return_text is not None:
        stdout.write(command_return_text)


def send_exc_notificatoin(instance_name: str, exception: BaseException) -> None:
    if not isatty(stderr.fileno()):
        from subprocess import run as subprocess_run
        from traceback import format_exception

        try:
            subprocess_run(
                (
                    "notify-send",
                    "--urgency",
                    "critical",
                    "--icon",
                    "bubblejail-config",
                    f"Failed to run instance: {instance_name}",
                    f"Exception: {format_exception(exception, limit=0)}",
                )
            )
        except FileNotFoundError:
            # Make notify-send optional
            ...


def run_bjail(
    instance_name: str,
    args_to_instance: list[str],
    wait: bool,
    dry_run: bool,
    debug_bwrap_args: list[list[str]],
    debug_shell: bool,
    debug_log_dbus: str | None,
    debug_helper_script: Path | None,
    wizard: bool,
) -> None:
    try:
        instance = BubblejailDirectories.instance_get(instance_name)

        if instance.is_running():
            if wizard:
                print(
                    "Configuration wizard can only be enabled if "
                    "instance is not running.",
                    file=stderr,
                )
                raise SystemExit(1)

            run_running_instance(
                instance=instance,
                args_to_instance=args_to_instance,
                wait=wait,
                dry_run=dry_run,
            )
            return
        else:
            extra_bwrap_args: list[str] | None
            if debug_bwrap_args is not None:
                extra_bwrap_args = []
                for x in debug_bwrap_args:
                    extra_bwrap_args.extend(_extra_args_converter(x))
            else:
                extra_bwrap_args = None

            log_dbus = DBusLogEnum.NONE
            if debug_log_dbus is not None:
                log_dbus = DBusLogEnum(debug_log_dbus)

            if wizard:
                if not isatty(stderr.fileno()):
                    print(
                        "Configuration wizard can only be enabled when run from terminal",
                        file=stderr,
                    )
                    raise SystemExit(1)

                log_dbus = DBusLogEnum.PARSE

            result = async_run(
                instance.async_run_init(
                    args_to_run=args_to_instance,
                    debug_shell=debug_shell,
                    debug_helper_script=debug_helper_script,
                    log_dbus=log_dbus,
                    dry_run=dry_run,
                    extra_bwrap_args=extra_bwrap_args,
                )
            )

            if wizard:
                if dbus_parser := result.dbus_proxy.dbus_parser:
                    from .wizard import DBusWizard

                    DBusWizard(instance, dbus_parser).run()
    except Exception as e:
        send_exc_notificatoin(instance_name, e)
        raise


def bjail_list(list_what: str) -> None:
    str_iterator: Iterator[str]

    if list_what == "instances":
        str_iterator = iter_instance_names()
    elif list_what == "profiles":
        str_iterator = BubblejailDirectories.iter_profile_names()
    elif list_what == "services":
        str_iterator = (x.name for x in SERVICES_CLASSES)
    elif list_what == "subcommands":
        str_iterator = iter_subcommands()

    for string in str_iterator:
        print(string, file=stdout)


def bjail_create(
    new_instance_name: str, profile: str | None, no_desktop_entry: bool
) -> None:
    BubblejailDirectories.create_new_instance(
        new_name=new_instance_name,
        profile_name=profile,
        create_dot_desktop=no_desktop_entry,
        print_import_tips=True,
    )


def bjail_edit(instance_name: str) -> None:
    instance = BubblejailDirectories.instance_get(instance_name)

    from tempfile import TemporaryDirectory

    with TemporaryDirectory("bubblejail-edit") as tempdir:
        # Create path to temporary file and write existing config
        temp_file_path = Path(tempdir + "temp.toml")
        with open(temp_file_path, mode="x") as tempfile:
            tempfile.write(instance.read_services_file())

        initial_modification_time = stat(temp_file_path).st_mtime
        # Launch EDITOR on the temporary file
        from subprocess import run as subprocess_run

        subprocess_run(
            args=(environ["EDITOR"], str(temp_file_path)),
            check=True,
        )

        # If file was not modified do nothing
        if initial_modification_time >= stat(temp_file_path).st_mtime:
            print("File not modified. Not overwriting config.", file=stderr)
            return

        from tomllib import loads as toml_loads

        from .services import ServiceContainer

        # Verify that the new config is valid
        with open(temp_file_path) as tempfile:
            new_config_toml = tempfile.read()
            ServiceContainer(toml_loads(new_config_toml))
        # Write to instance config file
        instance.save_services_file(new_config_toml)


def bjail_create_desktop_entry(
    instance_name: str, profile: str | None, desktop_entry: str | None
) -> None:
    BubblejailDirectories.overwrite_desktop_entry_for_profile(
        instance_name=instance_name,
        profile_name=profile,
        desktop_entry_name=desktop_entry,
    )


COMMANDS_FUNCS: dict[str, Callable[..., None]] = {
    "run": run_bjail,
    "create": bjail_create,
    "list": bjail_list,
    "edit": bjail_edit,
    "generate-desktop-entry": bjail_create_desktop_entry,
}


def create_arg_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=("Bubblejail is a bubblewrap based sandboxing utility.")
    )
    subparsers = parser.add_subparsers(
        required=True, description="Available subcommands."
    )
    for subcommand_name, subcommand_data in BUBBLEJAIL_CMD.items():
        subfunction = COMMANDS_FUNCS[subcommand_name]
        description = subcommand_data["description"]
        subcommand_add_argument = subcommand_data["add_argument"]
        subparser = subparsers.add_parser(
            subcommand_name,
            description=description,
        )
        subparser.set_defaults(
            func=subfunction,
        )
        for arg_name, arg_options in subcommand_add_argument.items():
            subparser.add_argument(
                arg_name,
                **arg_options,
            )

    return parser


def bubblejail_main(arg_list: list[str] | None = None) -> None:
    # Short circuit to auto-complete
    if len(argv) > 1 and argv[1] == "auto-complete":
        from .bubblejail_cli_autocomplete import run_autocomplete

        run_autocomplete()
        return

    parser = create_arg_parser()
    parser.add_argument(
        "--version",
        action="version",
        version=BubblejailSettings.VERSION,
    )

    args_dict = vars(parser.parse_args(arg_list))

    func = args_dict.pop("func")

    func(**args_dict)
