# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2019-2022 igo95862
from __future__ import annotations

from asyncio import (
    CancelledError,
    Event,
    create_subprocess_exec,
    get_running_loop,
    wait_for,
)
from contextlib import ExitStack
from dataclasses import dataclass, field, fields
from enum import IntFlag
from enum import auto as enum_auto
from functools import cache
from multiprocessing import Process
from os import O_CLOEXEC, O_NONBLOCK, environ, getpid, getuid, pipe2, readlink
from pathlib import Path
from shutil import which
from sys import stderr
from typing import TYPE_CHECKING, Any, ClassVar, NotRequired, TypedDict, cast

from xdg import BaseDirectory

from .bwrap_config import (
    Bind,
    BwrapConfigBase,
    BwrapRawArgs,
    ChangeDir,
    DbusCommon,
    DbusSessionCall,
    DbusSessionOwn,
    DbusSessionRawArg,
    DbusSessionSee,
    DbusSessionTalkTo,
    DbusSystemRawArg,
    DevBind,
    DevBindTry,
    DirCreate,
    EnvironVar,
    FileTransfer,
    LaunchArguments,
    ReadOnlyBind,
    ReadOnlyBindTry,
    SeccompDirective,
    SeccompSyscallErrno,
    ShareNetwork,
    Symlink,
)
from .exceptions import (
    BubblejailDependencyError,
    BubblejailInitializationError,
    ServiceConflictError,
)
from .utils import aread_once

if TYPE_CHECKING:
    from asyncio.subprocess import Process as AsyncioProcess
    from collections.abc import Awaitable, Callable, Generator, Iterator
    from dataclasses import Field

    from _typeshed import DataclassInstance
    from cattrs import Converter


class ServiceWantsSend: ...


class ServiceWantsHomeBind(ServiceWantsSend): ...


class ServiceWantsDbusSessionBind(ServiceWantsSend): ...


if TYPE_CHECKING:
    ServiceIterTypes = (
        BwrapConfigBase
        | FileTransfer
        | SeccompDirective
        | LaunchArguments
        | ServiceWantsSend
        | DbusCommon
    )

    ServiceSendType = Path

    ServiceGeneratorType = Generator[ServiceIterTypes, ServiceSendType, None]


ServiceSettingsTypes = str | list[str] | bool | int
ServiceSettingsDict = dict[str, ServiceSettingsTypes]
ServicesConfDictType = dict[str, ServiceSettingsDict]


class ServiceFlags(IntFlag):
    DEPRECATED = enum_auto()
    EXPERIMENTAL = enum_auto()
    NO_GUI = enum_auto()


class SettingFieldMetadata(TypedDict):
    pretty_name: str
    description: str
    flags: NotRequired[ServiceFlags]


XDG_DESKTOP_VARS: frozenset[str] = frozenset(
    {
        "XDG_CURRENT_DESKTOP",
        "DESKTOP_SESSION",
        "XDG_SESSION_TYPE",
        "XDG_SESSION_DESKTOP",
    }
)


def generate_path_var() -> str:
    """Filters PATH variable to locations with /usr prefix"""

    # Split by semicolon
    paths = environ["PATH"].split(":")
    # Filter by /usr and /tmp then join by semicolon
    return ":".join(
        filter(lambda s: s.startswith("/usr/") or s == "/bin" or s == "/sbin", paths)
    )


def generate_toolkits() -> Generator[ServiceIterTypes, None, None]:
    config_home_path = Path(BaseDirectory.xdg_config_home)
    kde_globals_conf = config_home_path / "kdeglobals"
    if kde_globals_conf.exists():
        yield ReadOnlyBind(kde_globals_conf)


@dataclass(slots=True)
class EmptySettings: ...


class BubblejailService:
    xdg_runtime_dir: ClassVar[Path] = Path(f"/run/user/{getuid()}")

    Settings: type[DataclassInstance] = EmptySettings

    def __init__(self, context: ServicesConfig):
        self.context = context

    def iter_bwrap_options(self) -> ServiceGeneratorType:
        yield from ()

    async def post_init_hook(self, pid: int) -> None: ...

    async def post_shutdown_hook(self) -> None: ...

    @classmethod
    def has_settings(cls) -> bool:
        return cls.Settings is not EmptySettings

    @classmethod
    def iter_settings_fields_and_meta(
        cls,
    ) -> Iterator[tuple[Field[Any], SettingFieldMetadata]]:
        for setting_field in fields(cls.Settings):
            setting_metadata = cast(
                SettingFieldMetadata,
                setting_field.metadata,
            )
            yield setting_field, setting_metadata

    name: ClassVar[str]
    pretty_name: ClassVar[str]
    description: ClassVar[str]
    conflicts: ClassVar[frozenset[str]] = frozenset()
    flags: ClassVar[ServiceFlags] = ServiceFlags(0)


# Pre version 0.6.0 home bind path
OLD_HOME_BIND = Path("/home/user")


class BubblejailDefaults(BubblejailService):

    def iter_bwrap_options(self) -> ServiceGeneratorType:
        # Distro packaged libraries and binaries
        yield ReadOnlyBind("/usr")
        yield ReadOnlyBind("/opt")
        # Recreate symlinks in / or mount them read-only if its not a symlink.
        # Should be portable between distros.
        for root_path in Path("/").iterdir():
            if (
                root_path.name.startswith("lib")  # /lib /lib64 /lib32
                or root_path.name == "bin"
                or root_path.name == "sbin"
            ):
                if root_path.is_symlink():
                    yield Symlink(readlink(root_path), root_path)
                else:
                    yield ReadOnlyBind(root_path)

        yield ReadOnlyBind("/etc")

        # Temporary directories
        yield DirCreate("/tmp")
        yield DirCreate("/var")

        # Sys directory and its immediate children
        yield DirCreate("/sys", permissions=0o700)
        for sysfs_child in (
            "/sys/block",
            "/sys/bus",
            "/sys/class",
            "/sys/dev",
            "/sys/devices",
        ):
            yield DirCreate(sysfs_child, permissions=0o0755)

        # CPU topology access
        yield ReadOnlyBind("/sys/devices/system/cpu")

        yield DirCreate(self.xdg_runtime_dir, permissions=0o700)

        # Bind pseudo home
        real_home = Path.home()
        home_path = yield ServiceWantsHomeBind()
        yield Bind(home_path, real_home)
        yield EnvironVar("HOME", str(real_home))
        # Compatibility symlink
        if real_home != OLD_HOME_BIND:
            yield Symlink(real_home, OLD_HOME_BIND)

        yield ChangeDir(real_home)

        # Set environmental variables
        from getpass import getuser

        yield EnvironVar("USER", getuser())
        yield EnvironVar("USERNAME", getuser())
        yield EnvironVar("PATH", generate_path_var())
        yield EnvironVar("XDG_RUNTIME_DIR", str(self.xdg_runtime_dir))

        yield EnvironVar("LANG")

        if not environ.get("BUBBLEJAIL_DISABLE_SECCOMP_DEFAULTS"):
            for blocked_syscal in (
                "bdflush",
                "io_pgetevents",
                "kexec_file_load",
                "kexec_load",
                "migrate_pages",
                "move_pages",
                "nfsservctl",
                "nice",
                "oldfstat",
                "oldlstat",
                "oldolduname",
                "oldstat",
                "olduname",
                "pciconfig_iobase",
                "pciconfig_read",
                "pciconfig_write",
                "sgetmask",
                "ssetmask",
                "swapcontext",
                "swapoff",
                "swapon",
                "sysfs",
                "uselib",
                "userfaultfd",
                "ustat",
                "vm86",
                "vm86old",
                "vmsplice",
                "bpf",
                "fanotify_init",
                "lookup_dcookie",
                "perf_event_open",
                "quotactl",
                "setdomainname",
                "sethostname",
                # "chroot",
                # Firefox and Chromium fails if chroot is not available
                "delete_module",
                "init_module",
                "finit_module",
                "query_module",
                "acct",
                "iopl",
                "ioperm",
                "settimeofday",
                "stime",
                "clock_settime",
                "clock_settime64",
                "vhangup",
            ):
                yield SeccompSyscallErrno(
                    blocked_syscal,
                    1,
                    skip_on_not_exists=True,
                )

        # Bind session socket inside the sandbox
        dbus_session_inside_path = self.xdg_runtime_dir / "bus"
        dbus_session_outside_path = yield ServiceWantsDbusSessionBind()
        yield EnvironVar(
            "DBUS_SESSION_BUS_ADDRESS", f"unix:path={dbus_session_inside_path}"
        )
        yield Bind(
            dbus_session_outside_path,
            dbus_session_inside_path,
        )

    def __repr__(self) -> str:
        return "Bubblejail defaults."

    name = "default"
    pretty_name = "Default settings"
    description = "Settings that must be present in any instance"


@dataclass(slots=True)
class CommonSettingsSettings:
    executable_name: str | list[str] = field(
        default="",
        metadata=SettingFieldMetadata(
            pretty_name="Default arguments",
            description=("Default arguments to run when no arguments were provided"),
        ),
    )
    share_local_time: bool = field(
        default=False,
        metadata=SettingFieldMetadata(
            pretty_name="Share local time",
            description="This option has no effect since version 0.6.0",
            flags=ServiceFlags.DEPRECATED,
        ),
    )
    filter_disk_sync: bool = field(
        default=False,
        metadata=SettingFieldMetadata(
            pretty_name="Filter disk sync",
            description=(
                "Do not allow flushing disk. "
                "Useful for EA Origin client that tries to flush "
                "to disk too often."
            ),
        ),
    )
    dbus_name: str = field(
        default="",
        metadata=SettingFieldMetadata(
            pretty_name="Application's D-Bus name",
            description="D-Bus name allowed to acquire and own",
        ),
    )


class CommonSettings(BubblejailService):
    Settings = CommonSettingsSettings

    def iter_bwrap_options(self) -> ServiceGeneratorType:
        settings = self.context.common
        if settings is None:
            raise RuntimeError

        # Executable main arguments
        if settings.executable_name:
            if isinstance(settings.executable_name, str):
                yield LaunchArguments([settings.executable_name])
            else:
                yield LaunchArguments(settings.executable_name)

        if settings.filter_disk_sync:
            yield SeccompSyscallErrno("sync", 0)
            yield SeccompSyscallErrno("fsync", 0)

        if dbus_name := settings.dbus_name:
            yield DbusSessionOwn(dbus_name)

    name = "common"
    pretty_name = "Common Settings"
    description = "Settings that don't fit in any particular category"


class X11(BubblejailService):

    @staticmethod
    def x11_socket_path(display_var: str) -> str | None:
        # See https://man.archlinux.org/man/X.7#DISPLAY_NAMES
        # protocol/hostname:displaynumber.screennumber
        match display_var.split("/"):
            case [protocol, remainder]:
                if protocol != "unix":
                    return None
                display_var = remainder
            case [remainder]:
                display_var = remainder
            case _:
                raise ValueError

        # hostname:displaynumber.screennumber
        match display_var.split(":"):
            case [hostname, remainder]:
                if hostname != "":
                    return None

                display_var = remainder
            case _:
                raise ValueError

        # displaynumber.screennumber
        match display_var.split("."):
            case [displaynumber, _]:
                ...
            case [displaynumber]:
                ...
            case _:
                raise ValueError

        return f"/tmp/.X11-unix/X{displaynumber}"

    def iter_bwrap_options(self) -> ServiceGeneratorType:

        for x in XDG_DESKTOP_VARS:
            if x not in environ:
                continue

            # Override the XDG_SESSION_TYPE on Xwayland to x11.
            # Otherwise some application will try to use Wayland without
            # access to socket.
            if (
                x == "XDG_SESSION_TYPE"
                and environ[x] == "wayland"
                and self.context.wayland is None
            ):
                yield EnvironVar(x, "x11")
                continue

            yield EnvironVar(x)

        yield EnvironVar("DISPLAY")

        if x11_socket_path := self.x11_socket_path(environ["DISPLAY"]):
            yield ReadOnlyBind(x11_socket_path)

        x_authority_path_str = environ.get("XAUTHORITY")
        if x_authority_path_str is not None:
            yield ReadOnlyBind(x_authority_path_str, "/tmp/.Xauthority")
            yield EnvironVar("XAUTHORITY", "/tmp/.Xauthority")

        yield from generate_toolkits()

    name = "x11"
    pretty_name = "X11 windowing system"
    description = (
        "Gives access to X11 socket.\n"
        "This is generally the default Linux windowing system."
    )


class Wayland(BubblejailService):
    def iter_bwrap_options(self) -> ServiceGeneratorType:

        try:
            wayland_display_env = environ["WAYLAND_DISPLAY"]
        except KeyError:
            print("wayland: No wayland display.", file=stderr)
            raise

        for x in XDG_DESKTOP_VARS:
            if x in environ:
                yield EnvironVar(x)

        yield EnvironVar("GDK_BACKEND", "wayland")
        yield EnvironVar("MOZ_DBUS_REMOTE", "1")
        yield EnvironVar("MOZ_ENABLE_WAYLAND", "1")

        yield EnvironVar("WAYLAND_DISPLAY", "wayland-0")
        original_socket_path = (
            Path(BaseDirectory.get_runtime_dir()) / wayland_display_env
        )

        new_socket_path = self.xdg_runtime_dir / "wayland-0"
        yield Bind(original_socket_path, new_socket_path)
        yield from generate_toolkits()

    name = "wayland"
    pretty_name = "Wayland windowing system"
    description = (
        "Make sure you are running Wayland session\n"
        "and your application supports Wayland"
    )


class Network(BubblejailService):
    def iter_bwrap_options(self) -> ServiceGeneratorType:
        # Systemd-resolved makes /etc/resolv.conf a symlink
        # to /run/systemd/resolve/stub-resolv.conf.
        # Same do some DHCP clients like NetworkManager.
        resolv_conf_path = Path("/etc/resolv.conf")
        actual_resolv_path = resolv_conf_path.resolve()
        if resolv_conf_path != actual_resolv_path:
            yield ReadOnlyBind(actual_resolv_path)

        yield ShareNetwork()

    name = "network"
    pretty_name = "Network access"
    description = "Gives access to network."
    conflicts = frozenset(("slirp4netns", "pasta_network"))


class PulseAudio(BubblejailService):
    def iter_bwrap_options(self) -> ServiceGeneratorType:

        yield Bind(
            f"{BaseDirectory.get_runtime_dir()}/pulse/native",
            self.xdg_runtime_dir / "pulse/native",
        )

    name = "pulse_audio"
    pretty_name = "Pulse Audio"
    description = "Default audio system in most distros"


@dataclass(slots=True)
class HomeShareSettings:
    home_paths: list[str] = field(
        default_factory=list,
        metadata=SettingFieldMetadata(
            pretty_name="List of paths",
            description="Path to share with sandbox",
        ),
    )


class HomeShare(BubblejailService):
    Settings = HomeShareSettings

    def iter_bwrap_options(self) -> ServiceGeneratorType:
        settings = self.context.home_share
        if settings is None:
            raise RuntimeError

        for path_relative_to_home in settings.home_paths:
            yield Bind(
                Path.home() / path_relative_to_home,
            )

    name = "home_share"
    pretty_name = "Home Share"
    description = "Share directories or files relative to home"


@dataclass(slots=True)
class DirectRenderingSettings:
    enable_aco: bool = field(
        default=False,
        metadata=SettingFieldMetadata(
            pretty_name="Enable ACO",
            description=(
                "Enables high performance vulkan shader "
                "compiler for AMD GPUs. Enabled by default "
                "since mesa 20.02"
            ),
            flags=ServiceFlags.DEPRECATED,
        ),
    )


class DirectRendering(BubblejailService):
    Settings = DirectRenderingSettings

    def iter_bwrap_options(self) -> ServiceGeneratorType:

        # TODO: Allow to select which DRM devices to pass

        # Bind /dev/dri and /sys/dev/char and /sys/devices
        # Get names of cardX and renderX in /dev/dri
        dev_dri_path = Path("/dev/dri/")
        device_names = set()
        for x in dev_dri_path.iterdir():
            if x.is_char_device():
                device_names.add(x.stem)

        # Resolve links in /sys/dev/char/
        sys_dev_char_path = Path("/sys/dev/char/")
        # For each symlink in /sys/dev/char/ resolve
        # and see if they point to cardX or renderX
        for x in sys_dev_char_path.iterdir():
            x_resolved = x.resolve()
            if x_resolved.name in device_names:
                # Found the dri device
                # Add the /sys/dev/char/ path
                yield Symlink(x_resolved, x)
                # Add the two times parent (parents[1])
                # Seems like the dri devices are stored as
                # /sys/devices/..pcie_id../drm/dri
                # We want to bind the /sys/devices/..pcie_id../
                yield DevBind(x_resolved.parents[1])

        yield DevBind("/dev/dri")

        # Nvidia specific binds
        for nv_dev in Path("/dev/").iterdir():
            if nv_dev.name.startswith("nvidia"):
                yield DevBind(nv_dev)

        # Nvidia driver 500+ requires read access to sysfs module directories
        # and CUDA does not work without them.
        for nv_mod in Path("/sys/module/").iterdir():
            if nv_mod.name.startswith("nvidia"):
                yield ReadOnlyBindTry(nv_mod)

    name = "direct_rendering"
    pretty_name = "Direct Rendering"
    description = "Provides access to GPU"


class Systray(BubblejailService):
    def iter_bwrap_options(self) -> ServiceGeneratorType:
        yield DbusSessionCall(
            "org.kde.StatusNotifierWatcher",
            object_path="/StatusNotifierWatcher",
        )

    name = "systray"
    pretty_name = "System tray icons"
    description = (
        "Provides access to D-Bus API for creating tray icons\n"
        "This is not the only way to create tray icons but\n"
        "the most common one."
    )


class Joystick(BubblejailService):
    def iter_bwrap_options(self) -> ServiceGeneratorType:
        look_for_names: set[str] = set()

        dev_input_path = Path("/dev/input")
        sys_class_input_path = Path("/sys/class/input")
        js_names: set[str] = set()
        for input_dev in dev_input_path.iterdir():
            if not input_dev.is_char_device():
                continue
            # If device dooes not have read permission
            # for others it is not a gamepad
            # Only jsX devices have this, we need to find eventX of gamepad
            if (input_dev.stat().st_mode & 0o004) == 0:
                continue

            js_names.add(input_dev.name)

        look_for_names.update(js_names)
        # Find event name of js device
        # Resolve the PCI name. Should be something like this:
        # /sys/devices/.../input/input23/js0
        # Iterate over names in this directory
        # and add eventX names
        for js_name in js_names:
            sys_class_input_js = sys_class_input_path / js_name

            js_reloved = sys_class_input_js.resolve()
            js_input_path = js_reloved.parents[0]
            for input_element in js_input_path.iterdir():
                if input_element.name.startswith("event"):
                    look_for_names.add(input_element.name)

        # Find the *-joystick in /dev/input/by-path/
        for dev_name in look_for_names:
            # Add /dev/input/X device
            yield DevBind(dev_input_path / dev_name)

            sys_class_path = sys_class_input_path / dev_name

            yield Symlink(
                readlink(sys_class_path),
                sys_class_path,
            )

            pci_path = sys_class_path.resolve()
            yield DevBind(pci_path.parents[2])

    name = "joystick"
    pretty_name = "Joysticks and gamepads"
    description = (
        "Windowing systems (x11 and wayland) do not support gamepads.\n"
        "Every game has to read from device files directly.\n"
        "This service provides access to them."
    )


@dataclass(slots=True)
class RootShareSettings:
    paths: list[str] = field(
        default_factory=list,
        metadata=SettingFieldMetadata(
            pretty_name="Read/Write paths",
            description="Path to share with sandbox",
        ),
    )
    read_only_paths: list[str] = field(
        default_factory=list,
        metadata=SettingFieldMetadata(
            pretty_name="Read only paths",
            description="Path to share read-only with sandbox",
        ),
    )


class RootShare(BubblejailService):
    Settings = RootShareSettings

    def iter_bwrap_options(self) -> ServiceGeneratorType:
        settings = self.context.root_share
        if settings is None:
            raise RuntimeError

        for x in settings.paths:
            yield Bind(x)

        for x in settings.read_only_paths:
            yield ReadOnlyBind(x)

    name = "root_share"
    pretty_name = "Root share"
    description = "Share directories or files relative to root /"


class OpenJDK(BubblejailService):
    name = "openjdk"
    pretty_name = "Java"
    description = "Enable for applications that require Java\n" "Example: Minecraft"

    flags = ServiceFlags.DEPRECATED


class Notifications(BubblejailService):
    def iter_bwrap_options(self) -> ServiceGeneratorType:
        yield DbusSessionCall(
            "org.freedesktop.Notifications",
            object_path="/org/freedesktop/Notifications",
        )

    name = "notify"
    pretty_name = "Notifications"
    description = "Ability to send notifications to desktop"


@dataclass(slots=True)
class GnomeToolkitSettings:
    gnome_portal: bool = field(
        default=False,
        metadata=SettingFieldMetadata(
            pretty_name="GNOME Portal",
            description="Access to GNOME Portal D-Bus API",
        ),
    )
    dconf_dbus: bool = field(
        default=False,
        metadata=SettingFieldMetadata(
            pretty_name="Dconf D-Bus",
            description="Access to dconf D-Bus API",
        ),
    )
    gnome_vfs_dbus: bool = field(
        default=False,
        metadata=SettingFieldMetadata(
            pretty_name="GNOME VFS",
            description="Access to GNOME Virtual File System D-Bus API",
        ),
    )


class GnomeToolkit(BubblejailService):
    Settings = GnomeToolkitSettings

    def iter_bwrap_options(self) -> ServiceGeneratorType:
        settings = self.context.gnome_toolkit
        if settings is None:
            raise RuntimeError

        if settings.gnome_portal:
            yield EnvironVar("GTK_USE_PORTAL", "1")
            yield DbusSessionTalkTo("org.freedesktop.portal.*")

        if settings.dconf_dbus:
            yield DbusSessionTalkTo("ca.desrt.dconf")

        if settings.gnome_vfs_dbus:
            yield DbusSessionTalkTo("org.gtk.vfs.*")

        # TODO: org.a11y.Bus accessibility services
        # Needs both dbus and socket, socket is address is
        # acquired from dbus

    name = "gnome_toolkit"
    pretty_name = "GNOME toolkit"
    description = "Access to GNOME APIs"
    flags = ServiceFlags.EXPERIMENTAL


class Pipewire(BubblejailService):
    def iter_bwrap_options(self) -> ServiceGeneratorType:
        PIPEWIRE_SOCKET_NAME = "pipewire-0"
        original_socket_path = (
            Path(BaseDirectory.get_runtime_dir()) / PIPEWIRE_SOCKET_NAME
        )

        new_socket_path = self.xdg_runtime_dir / "pipewire-0"

        yield ReadOnlyBind(original_socket_path, new_socket_path)

    name = "pipewire"
    pretty_name = "Pipewire"
    description = "Pipewire sound and screencapture system"


class VideoForLinux(BubblejailService):
    def iter_bwrap_options(self) -> ServiceGeneratorType:

        yield DevBindTry("/dev/v4l")
        yield DevBindTry("/sys/class/video4linux")
        yield DevBindTry("/sys/bus/media/")

        try:
            sys_v4l_iterator = Path("/sys/class/video4linux").iterdir()
            for sys_path in sys_v4l_iterator:
                pcie_path = sys_path.resolve()

                for char_path in Path("/sys/dev/char/").iterdir():
                    if char_path.resolve() == pcie_path:
                        yield Symlink(readlink(char_path), char_path)

                yield DevBind(pcie_path.parents[1])
        except FileNotFoundError:
            ...

        for dev_path in Path("/dev").iterdir():

            name = dev_path.name

            if not (name.startswith("video") or name.startswith("media")):
                continue

            if not name[5:].isnumeric():
                continue

            yield DevBind(dev_path)

    name = "v4l"
    pretty_name = "Video4Linux"
    description = "Video capture. (webcams and etc.)"


class IBus(BubblejailService):
    def iter_bwrap_options(self) -> ServiceGeneratorType:
        yield EnvironVar("IBUS_USE_PORTAL", "1")
        yield EnvironVar("GTK_IM_MODULE", "ibus")
        yield EnvironVar("QT_IM_MODULE", "ibus")
        yield EnvironVar("XMODIFIERS", "@im=ibus")
        yield EnvironVar("GLFW_IM_MODULE", "ibus")
        yield DbusSessionTalkTo("org.freedesktop.portal.IBus.*")

    name = "ibus"
    pretty_name = "IBus input method"
    description = (
        "Gives access to IBus input method.\n"
        "This is generally the default input method for multilingual input."
    )
    conflicts = frozenset(("fcitx",))


class Fcitx(BubblejailService):

    def iter_bwrap_options(self) -> ServiceGeneratorType:
        yield EnvironVar("GTK_IM_MODULE", "fcitx")
        yield EnvironVar("QT_IM_MODULE", "fcitx")
        yield EnvironVar("XMODIFIERS", "@im=fcitx")
        yield EnvironVar("SDL_IM_MODULE", "fcitx")
        yield EnvironVar("GLFW_IM_MODULE", "ibus")
        yield DbusSessionTalkTo("org.freedesktop.portal.Fcitx.*")
        yield DbusSessionTalkTo("org.freedesktop.portal.IBus.*")

    name = "fcitx"
    pretty_name = "Fcitx/Fcitx5 input method"
    description = (
        "Gives access to Fcitx/Fcitx5 input method.\n"
        "This is another popular input method framework."
    )
    conflicts = frozenset(("ibus",))


@dataclass(slots=True)
class Slirp4netnsSettings:
    dns_servers: list[str] = field(
        default_factory=list,
        metadata=SettingFieldMetadata(
            pretty_name="DNS servers",
            description=("DNS servers used. " "Internal DNS server is always used."),
        ),
    )
    outbound_addr: str = field(
        default="",
        metadata=SettingFieldMetadata(
            pretty_name="Outbound address or device",
            description=(
                "Address or device to bind to. "
                "If not set the default address would be used."
            ),
        ),
    )
    disable_host_loopback: bool = field(
        default=True,
        metadata=SettingFieldMetadata(
            pretty_name="Disable host loopback access",
            description=("Prohibit connecting to host's loopback interface"),
        ),
    )


class Slirp4netns(BubblejailService):
    Settings = Slirp4netnsSettings

    def __init__(self, context: ServicesConfig) -> None:
        super().__init__(context)
        self.slirp_process: AsyncioProcess | None = None

    def iter_bwrap_options(self) -> ServiceGeneratorType:
        settings = self.context.slirp4netns
        if settings is None:
            raise RuntimeError

        self.outbound_addr = settings.outbound_addr
        self.disable_host_loopback = settings.disable_host_loopback

        dns_servers = settings.dns_servers.copy()
        dns_servers.append("10.0.2.3")

        # Systemd-resolved makes /etc/resolv.conf a symlink
        # to /run/systemd/resolve/stub-resolv.conf.
        # Same do some DHCP clients like NetworkManager.
        resolv_conf_path = Path("/etc/resolv.conf")
        actual_resolv_path = resolv_conf_path.resolve()
        if resolv_conf_path != actual_resolv_path:
            resolv_conf_path = actual_resolv_path

        yield FileTransfer(
            b"\n".join(f"nameserver {x}".encode() for x in dns_servers),
            resolv_conf_path,
        )

    async def post_init_hook(self, pid: int) -> None:
        settings = self.context.slirp4netns
        if settings is None:
            raise RuntimeError

        outbound_addr = settings.outbound_addr
        disable_host_loopback = settings.disable_host_loopback

        from lxns.namespaces import NetworkNamespace

        with ExitStack() as exit_stack:
            target_namespace = exit_stack.enter_context(NetworkNamespace.from_pid(pid))
            parent_ns = exit_stack.enter_context(target_namespace.get_user_namespace())
            parent_ns_fd = parent_ns.fileno()
            parent_ns_path = f"/proc/{getpid()}/fd/{parent_ns_fd}"

            ready_pipe_read, ready_pipe_write = pipe2(O_NONBLOCK | O_CLOEXEC)
            exit_stack.enter_context(open(ready_pipe_write))
            ready_pipe = exit_stack.enter_context(open(ready_pipe_read))

            loop = get_running_loop()
            slirp_ready_event = Event()
            loop.add_reader(ready_pipe_read, slirp_ready_event.set)

            slirp_bin_path = which("slirp4netns")
            if not slirp_bin_path:
                raise BubblejailDependencyError("slirp4netns binary not found")

            slirp4netns_args = [
                slirp_bin_path,
                f"--ready={ready_pipe_write}",
                "--configure",
                f"--userns-path={parent_ns_path}",
            ]

            if outbound_addr:
                slirp4netns_args.append((f"--outbound-addr={outbound_addr}"))

            if disable_host_loopback:
                slirp4netns_args.append("--disable-host-loopback")

            slirp4netns_args.append(str(pid))
            slirp4netns_args.append("tap0")

            self.slirp_process = await create_subprocess_exec(
                *slirp4netns_args,
                pass_fds=[ready_pipe_write],
            )

            slirp_ready_task = loop.create_task(
                slirp_ready_event.wait(),
                name="slirp4netns ready",
            )

            early_process_end_task = loop.create_task(
                self.slirp_process.wait(), name="Early slirp4netns process end"
            )
            early_process_end_task.add_done_callback(
                lambda _: slirp_ready_task.cancel()
            )

            try:
                await wait_for(slirp_ready_task, timeout=3)
            except CancelledError:
                raise BubblejailInitializationError("Slirp4netns initialization failed")
            finally:
                loop.remove_reader(ready_pipe_read)
                early_process_end_task.cancel()

            ready_pipe.read()

    async def post_shutdown_hook(self) -> None:
        try:
            if self.slirp_process is not None:
                self.slirp_process.terminate()
                await wait_for(self.slirp_process.wait(), timeout=3)
        except ProcessLookupError:
            ...

    name = "slirp4netns"
    pretty_name = "Slirp4netns networking"
    description = (
        "Independent networking stack for sandbox. " "Requires slirp4netns executable."
    )
    conflicts = frozenset(("network", "pasta_network"))


@dataclass(slots=True)
class NamespacesLimitsSettings:
    user: int = field(
        default=0,
        metadata=SettingFieldMetadata(
            pretty_name="Max number of user namespaces",
            description=(
                "Limiting user namespaces blocks acquiring new "
                "capabilities and privileges inside namespaces."
            ),
        ),
    )
    mount: int = field(
        default=0,
        metadata=SettingFieldMetadata(
            pretty_name="Max number of mount namespaces",
            description=("Limits number mount namespaces."),
        ),
    )
    pid: int = field(
        default=0,
        metadata=SettingFieldMetadata(
            pretty_name="Max number of PID namespaces",
            description=("Limits number PID namespaces."),
        ),
    )
    ipc: int = field(
        default=0,
        metadata=SettingFieldMetadata(
            pretty_name="Max number of IPC namespaces",
            description=("Limits number IPC namespaces."),
        ),
    )
    net: int = field(
        default=0,
        metadata=SettingFieldMetadata(
            pretty_name="Max number of net namespaces",
            description=("Limits number net namespaces."),
        ),
    )
    time: int = field(
        default=0,
        metadata=SettingFieldMetadata(
            pretty_name="Max number of time namespaces",
            description=("Limits number time namespaces."),
        ),
    )
    uts: int = field(
        default=0,
        metadata=SettingFieldMetadata(
            pretty_name="Max number of UTS namespaces",
            description=("Limits number UTS namespaces."),
        ),
    )
    cgroup: int = field(
        default=0,
        metadata=SettingFieldMetadata(
            pretty_name="Max number of cgroups namespaces",
            description=("Limits number cgroups namespaces."),
        ),
    )


class NamespacesLimits(BubblejailService):
    Settings = NamespacesLimitsSettings

    @staticmethod
    def set_namespaces_limits(
        pid: int,
        namespace_files_to_limits: dict[str, int],
    ) -> None:
        from lxns.namespaces import UserNamespace

        with (
            UserNamespace.from_pid(pid) as target_namespace,
            target_namespace.get_user_namespace() as parent_ns,
        ):
            if parent_ns.ns_id != UserNamespace.get_current_ns_id():
                parent_ns.setns()
            else:
                print(
                    "namespaces_limits: Already in parent user namespace", file=stderr
                )

            target_namespace.setns()

        for proc_file, limit_to_set in namespace_files_to_limits.items():
            with open("/proc/sys/user/" + proc_file, mode="w") as f:
                f.write(str(limit_to_set))

    async def post_init_hook(self, pid: int) -> None:
        settings = self.context.namespaces_limits
        if settings is None:
            raise RuntimeError

        namespace_files_to_limits: dict[str, int] = {}
        if (user_ns_limit := settings.user) >= 0:
            namespace_files_to_limits["max_user_namespaces"] = (
                user_ns_limit and user_ns_limit + 1
            )

        if (mount_ns_limit := settings.mount) >= 0:
            namespace_files_to_limits["max_mnt_namespaces"] = (
                mount_ns_limit and mount_ns_limit + 1
            )

        if (pid_ns_limit := settings.pid) >= 0:
            namespace_files_to_limits["max_pid_namespaces"] = (
                pid_ns_limit and pid_ns_limit + 1
            )

        if (ipc_ns_limit := settings.ipc) >= 0:
            namespace_files_to_limits["max_ipc_namespaces"] = (
                ipc_ns_limit and ipc_ns_limit + 1
            )

        if (net_ns_limit := settings.net) >= 0:
            if self.context.network is None:
                net_ns_limit += 1

            namespace_files_to_limits["max_net_namespaces"] = net_ns_limit

        if (time_ns_limit := settings.time) >= 0:
            namespace_files_to_limits["max_time_namespaces"] = time_ns_limit

        if (uts_ns_limit := settings.uts) >= 0:
            namespace_files_to_limits["max_uts_namespaces"] = (
                uts_ns_limit and uts_ns_limit + 1
            )

        if (cgroup_ns_limit := settings.cgroup) >= 0:
            namespace_files_to_limits["max_cgroup_namespaces"] = (
                cgroup_ns_limit and cgroup_ns_limit + 1
            )

        setter_process = Process(
            target=self.set_namespaces_limits, args=(pid, namespace_files_to_limits)
        )
        try:
            setter_process.start()
            setter_process.join(3)
            if setter_process.exitcode is None:
                setter_process.kill()
                setter_process.join(1)
                raise BubblejailInitializationError(
                    "Limit namespaces subprocess timed out"
                )
            elif setter_process.exitcode != 0:
                raise BubblejailInitializationError(
                    "Limit namespaces subprocess failed"
                )
        finally:
            setter_process.close()

    name = "namespaces_limits"
    pretty_name = "Limit namespaces"
    description = (
        "Limit number of namespaces available inside sandbox. "
        "Namespace limits are recursive. Setting limit 0 blocks "
        "creating new namespaces. Setting -1 unlocks the limit."
    )


@dataclass(slots=True)
class DebugSettings:
    raw_bwrap_args: list[str] = field(
        default_factory=list,
        metadata=SettingFieldMetadata(
            pretty_name="Raw bwrap args",
            description=(
                "Raw arguments to add to bwrap invocation. "
                "See bubblewrap documentation."
            ),
        ),
    )
    raw_dbus_session_args: list[str] = field(
        default_factory=list,
        metadata=SettingFieldMetadata(
            pretty_name="Raw xdg-dbus-proxy session args",
            description=(
                "Raw arguments to add to xdg-dbus-proxy session "
                "invocation. See xdg-dbus-proxy documentation."
            ),
        ),
    )
    raw_dbus_system_args: list[str] = field(
        default_factory=list,
        metadata=SettingFieldMetadata(
            pretty_name="Raw xdg-dbus-proxy system args",
            description=(
                "Raw arguments to add to xdg-dbus-proxy system "
                "invocation. See xdg-dbus-proxy documentation."
            ),
        ),
    )


class Debug(BubblejailService):
    Settings = DebugSettings

    def iter_bwrap_options(self) -> ServiceGeneratorType:
        settings = self.context.debug
        if settings is None:
            raise RuntimeError

        if raw_bwrap_args := settings.raw_bwrap_args:
            yield BwrapRawArgs(raw_bwrap_args)

        for dbus_session_raw_arg in settings.raw_dbus_session_args:
            yield DbusSessionRawArg(dbus_session_raw_arg)

        for dbus_system_raw_arg in settings.raw_dbus_system_args:
            yield DbusSystemRawArg(dbus_system_raw_arg)

    name = "debug"
    pretty_name = "Debug options"
    description = (
        "Various debug options such as adding arguments "
        "to the bwrap or xdg-dbus-proxy."
    )
    flags = ServiceFlags.NO_GUI


class GameMode(BubblejailService):
    def iter_bwrap_options(self) -> ServiceGeneratorType:
        yield DbusSessionCall(
            "com.feralinteractive.GameMode",
            object_path="/com/feralinteractive/GameMode",
        )

    name = "gamemode"
    pretty_name = "GameMode"
    description = (
        "Provides D-Bus access to the Feral's GameMode daemon D-Bus API. "
        "Use `gamemoderun` command to run a specific game with optimizations. "
        "For example, add `gamemoderun %command%` to Steam game launch options."
    )


@dataclass(slots=True)
class PastaNetworkSettings:
    extra_args: list[str] = field(
        default_factory=list,
        metadata=SettingFieldMetadata(
            pretty_name="Extra arguments",
            description=(
                "Extra arguments to pass to pasta. For example, interface "
                "binding, port forwarding... See `passt` man page."
            ),
        ),
    )


class PastaNetwork(BubblejailService):
    Settings = PastaNetworkSettings

    def __init__(self, context: ServicesConfig) -> None:
        super().__init__(context)
        self.pasta_process: AsyncioProcess | None = None

    async def post_init_hook(self, pid: int) -> None:
        settings = self.context.pasta_network
        if settings is None:
            raise RuntimeError

        pasta_args: list[str] = ["pasta", "--config-net", "--foreground"]

        from lxns.namespaces import NetworkNamespace

        with ExitStack() as exit_stack:
            self_pid = getpid()

            network_namespace = exit_stack.enter_context(NetworkNamespace.from_pid(pid))
            parent_ns = exit_stack.enter_context(network_namespace.get_user_namespace())
            pasta_args.extend(("--userns", f"/proc/{self_pid}/fd/{parent_ns.fileno()}"))

            ready_pipe_read_fd, ready_pipe_write_fd = pipe2(O_NONBLOCK | O_CLOEXEC)
            exit_stack.enter_context(open(ready_pipe_write_fd))
            ready_pipe = exit_stack.enter_context(open(ready_pipe_read_fd, mode="rb"))

            pasta_args.extend(("--pid", f"/proc/{self_pid}/fd/{ready_pipe_write_fd}"))

            self.pasta_process = await create_subprocess_exec(
                *pasta_args, *settings.extra_args, str(pid)
            )

            await aread_once(ready_pipe)

    async def post_shutdown_hook(self) -> None:
        if self.pasta_process is None:
            return

        try:
            self.pasta_process.terminate()
            await wait_for(self.pasta_process.wait(), timeout=3)
        except TimeoutError:
            self.pasta_process.kill()
        except ProcessLookupError:
            ...

    name = "pasta_network"
    pretty_name = "pasta networking"
    description = "Independent networking stack for sandbox. Requires pasta executable."
    conflicts = frozenset(("network", "slirp4netns"))


@dataclass(slots=True)
class MprisSettings:
    player_name: str = field(
        metadata=SettingFieldMetadata(
            pretty_name="Player's D-Bus name",
            description=(
                "D-Bus name suffix the player wants to acquire. "
                "Accepts glob patterns. (for example `firefox.*`)"
            ),
        ),
    )


class Mpris(BubblejailService):
    Settings = MprisSettings

    def iter_bwrap_options(self) -> ServiceGeneratorType:
        settings = self.context.mpris
        if settings is None:
            raise RuntimeError

        yield DbusSessionOwn(f"org.mpris.MediaPlayer2.{settings.player_name}")

    name = "mpris"
    pretty_name = "MPRIS"
    description = "Media Player Remote Interfacing Specification"


@dataclass(slots=True)
class XdgDesktopPortalSettings:
    add_flatpak_info: bool = field(
        default=False,
        metadata=SettingFieldMetadata(
            pretty_name="Add .flatpak-info",
            description=(
                "Add /.flatpak-info file to sandbox which some applications "
                "use as a trigger to use portals."
            ),
        ),
    )
    file_chooser: bool = field(
        default=True,
        metadata=SettingFieldMetadata(
            pretty_name="Enable File Chooser portal",
            description=(
                "Enable File Chooser portal which allows "
                "spawning file chooser outside sandbox."
            ),
        ),
    )
    global_shortcuts: bool = field(
        default=True,
        metadata=SettingFieldMetadata(
            pretty_name="Enable Global Shortcuts portal",
            description=(
                "Enable Global Shortcuts portal which allows "
                "application to create shortcuts that will work on Wayland."
            ),
        ),
    )
    inhibit: bool = field(
        default=True,
        metadata=SettingFieldMetadata(
            pretty_name="Enable Inhibit portal",
            description=(
                "Enable Inhibit portal which allows "
                "application to prevent desktop from suspending or idling."
            ),
        ),
    )
    notification: bool = field(
        default=True,
        metadata=SettingFieldMetadata(
            pretty_name="Enable Notification portal",
            description=(
                "Enable Notification portal which allows "
                "application to send notifications."
            ),
        ),
    )
    open_uri: bool = field(
        default=True,
        metadata=SettingFieldMetadata(
            pretty_name="Enable OpenURI portal",
            description=(
                "Enable OpenUri portal which allows opening " "files and links."
            ),
        ),
    )
    settings: bool = field(
        default=True,
        metadata=SettingFieldMetadata(
            pretty_name="Enable Settings portal",
            description=(
                "Enable Settings portal which allows "
                "reading common GUI settings like dark mode."
            ),
        ),
    )
    trash: bool = field(
        default=True,
        metadata=SettingFieldMetadata(
            pretty_name="Enable Trash portal",
            description=(
                "Enable Trash portal which allows "
                "sending trashed files to unified location outside sandbox."
            ),
        ),
    )


class XdgDesktopPortal(BubblejailService):
    Settings = XdgDesktopPortalSettings

    def iter_bwrap_options(self) -> ServiceGeneratorType:
        settings = self.context.xdg_desktop_portal
        if settings is None:
            raise RuntimeError

        yield DbusSessionSee("org.freedesktop.portal.Desktop")
        # Required to read "version" property of each portal interface
        yield DbusSessionCall(
            bus_name="org.freedesktop.portal.Desktop",
            interface_method="org.freedesktop.DBus.Properties.*",
            object_path="/org/freedesktop/portal/desktop",
        )
        # Interfaces that are used by multiple portals to wait for
        # user interaction.
        yield DbusSessionCall(
            bus_name="org.freedesktop.portal.Desktop",
            interface_method="org.freedesktop.portal.Request.*",
            object_path="/org/freedesktop/portal/desktop",
        )
        yield DbusSessionCall(
            bus_name="org.freedesktop.portal.Desktop",
            interface_method="org.freedesktop.portal.Session.*",
            object_path="/org/freedesktop/portal/desktop",
        )
        # GTK_USE_PORTAL=1 seems to still have effect on Firefox
        # but GDK_DEBUG=portals does not.
        yield EnvironVar("GTK_USE_PORTAL", "1")

        if settings.add_flatpak_info:
            yield FileTransfer(b"", "/.flatpak-info")

        if settings.file_chooser:
            yield DbusSessionCall(
                bus_name="org.freedesktop.portal.Desktop",
                interface_method="org.freedesktop.portal.FileChooser.*",
                object_path="/org/freedesktop/portal/desktop",
            )

        if settings.global_shortcuts:
            yield DbusSessionCall(
                bus_name="org.freedesktop.portal.Desktop",
                interface_method="org.freedesktop.portal.GlobalShortcuts.*",
                object_path="/org/freedesktop/portal/desktop",
            )

        if settings.inhibit:
            yield DbusSessionCall(
                bus_name="org.freedesktop.portal.Desktop",
                interface_method="org.freedesktop.portal.Inhibit.*",
                object_path="/org/freedesktop/portal/desktop",
            )

        if settings.notification:
            yield DbusSessionCall(
                bus_name="org.freedesktop.portal.Desktop",
                interface_method="org.freedesktop.portal.Notification.*",
                object_path="/org/freedesktop/portal/desktop",
            )

        if settings.open_uri:
            yield DbusSessionCall(
                bus_name="org.freedesktop.portal.Desktop",
                interface_method="org.freedesktop.portal.OpenURI.*",
                object_path="/org/freedesktop/portal/desktop",
            )

        if settings.settings:
            yield DbusSessionCall(
                bus_name="org.freedesktop.portal.Desktop",
                interface_method="org.freedesktop.portal.Settings.*",
                object_path="/org/freedesktop/portal/desktop",
            )

        if settings.trash:
            yield DbusSessionCall(
                bus_name="org.freedesktop.portal.Desktop",
                interface_method="org.freedesktop.portal.Trash.*",
                object_path="/org/freedesktop/portal/desktop",
            )

    name = "xdg_desktop_portal"
    pretty_name = "XDG Desktop Portal"
    description = (
        "D-Bus API that allows access for sandboxed application "
        "to resources outside of it."
    )
    flags = ServiceFlags.EXPERIMENTAL


SERVICES_CLASSES: tuple[type[BubblejailService], ...] = (
    CommonSettings,
    X11,
    Wayland,
    Network,
    PulseAudio,
    HomeShare,
    DirectRendering,
    Systray,
    Joystick,
    RootShare,
    OpenJDK,
    Notifications,
    GnomeToolkit,
    Pipewire,
    VideoForLinux,
    IBus,
    Fcitx,
    Slirp4netns,
    NamespacesLimits,
    Debug,
    GameMode,
    PastaNetwork,
    Mpris,
    XdgDesktopPortal,
)

SERVICES_MAP: dict[str, type[BubblejailService]] = {
    service.name: service for service in SERVICES_CLASSES
}


@dataclass(slots=True)
class ServicesConfig:
    common: CommonSettingsSettings | None = None
    x11: EmptySettings | None = None
    wayland: EmptySettings | None = None
    network: EmptySettings | None = None
    pulse_audio: EmptySettings | None = None
    home_share: HomeShareSettings | None = None
    direct_rendering: DirectRenderingSettings | None = None
    systray: EmptySettings | None = None
    joystick: EmptySettings | None = None
    root_share: RootShareSettings | None = None
    openjdk: EmptySettings | None = None
    notify: EmptySettings | None = None
    gnome_toolkit: GnomeToolkitSettings | None = None
    pipewire: EmptySettings | None = None
    v4l: EmptySettings | None = None
    ibus: EmptySettings | None = None
    fcitx: EmptySettings | None = None
    slirp4netns: Slirp4netnsSettings | None = None
    namespaces_limits: NamespacesLimitsSettings | None = None
    debug: DebugSettings | None = None
    gamemode: EmptySettings | None = None
    pasta_network: PastaNetworkSettings | None = None
    mpris: MprisSettings | None = None
    xdg_desktop_portal: XdgDesktopPortalSettings | None = None


class ServiceContainer:
    def __init__(self, conf_dict: ServicesConfDictType | None = None):
        self.services_config = ServicesConfig()
        self.services: dict[str, BubblejailService] = {}

        self.default_service = BubblejailDefaults(self.services_config)

        if conf_dict is not None:
            self.set_services(conf_dict)

    def set_services(self, new_services_datas: ServicesConfDictType) -> None:

        declared_services: set[str] = set()
        self.services.clear()
        self.services_config = self.get_cattrs_converter().structure(
            new_services_datas, ServicesConfig
        )

        for service_name in new_services_datas.keys():
            service_class = SERVICES_MAP[service_name]
            self.services[service_name] = service_class(self.services_config)

            declared_services.add(service_name)

            if conflicting_services := (declared_services & service_class.conflicts):
                raise ServiceConflictError(
                    f"Service conflict between {service_name} and "
                    f"{', '.join(conflicting_services)}"
                )

    @cache
    def get_cattrs_converter(self) -> Converter:
        from cattrs import Converter

        new_converter = Converter(omit_if_default=True, forbid_extra_keys=True)

        @new_converter.register_structure_hook
        def structure_str_or_list_str(val: Any, _: Any) -> str | list[str]:
            if isinstance(val, str):
                return val
            else:
                return new_converter.structure(val, list[str])

        return new_converter

    def get_service_conf_dict(self) -> ServicesConfDictType:
        conf_dict: ServicesConfDictType = self.get_cattrs_converter().unstructure(
            self.services_config, ServicesConfig
        )
        return conf_dict

    def iter_services(
        self,
        iter_default: bool = True,
    ) -> Iterator[BubblejailService]:

        if iter_default:
            yield self.default_service

        yield from self.services.values()

    def iter_post_init_hooks(self) -> Iterator[Callable[[int], Awaitable[None]]]:
        for service in self.services.values():
            if service.__class__.post_init_hook is BubblejailService.post_init_hook:
                continue

            yield service.post_init_hook

    def iter_post_shutdown_hooks(self) -> Iterator[Callable[[], Awaitable[None]]]:
        for service in self.services.values():
            if (
                service.__class__.post_shutdown_hook
                is BubblejailService.post_shutdown_hook
            ):
                continue

            yield service.post_shutdown_hook

    @classmethod
    def get_services_settings_metadata(
        cls,
    ) -> dict[str, dict[str, SettingFieldMetadata]]:

        return {
            service_name: {
                setting_field.name: setting_metadata
                for setting_field, setting_metadata in service.iter_settings_fields_and_meta()
            }
            for service_name, service in SERVICES_MAP.items()
        }
