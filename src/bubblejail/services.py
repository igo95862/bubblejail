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
from __future__ import annotations

from asyncio import (
    CancelledError,
    Event,
    create_subprocess_exec,
    get_running_loop,
    wait_for,
)
from dataclasses import (
    asdict,
    dataclass,
    field,
    fields,
    is_dataclass,
    make_dataclass,
)
from multiprocessing import Process
from os import O_CLOEXEC, O_NONBLOCK, environ, getpid, getuid, pipe2, readlink
from pathlib import Path
from platform import machine
from shutil import which
from typing import TYPE_CHECKING, TypedDict

from xdg import BaseDirectory

from .bwrap_config import (
    Bind,
    BwrapConfigBase,
    ChangeDir,
    DbusCommon,
    DbusSessionOwn,
    DbusSessionTalkTo,
    DevBind,
    DevBindTry,
    DirCreate,
    EnvrimentalVar,
    FileTransfer,
    LaunchArguments,
    ReadOnlyBind,
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

if TYPE_CHECKING:
    from asyncio.subprocess import Process as AsyncioProcess
    from collections.abc import Awaitable, Callable, Generator, Iterator
    from dataclasses import Field
    from typing import Any, ClassVar, Type, TypeVar

    from _typeshed import DataclassInstance

# region Service Typing


class ServiceWantsSend:
    ...


class ServiceWantsHomeBind(ServiceWantsSend):
    ...


class ServiceWantsDbusSessionBind(ServiceWantsSend):
    ...


if TYPE_CHECKING:
    ServiceIterTypes = (
        BwrapConfigBase | FileTransfer |
        SeccompDirective | LaunchArguments |
        ServiceWantsSend | DbusCommon
    )

    ServiceSendType = Path

    ServiceGeneratorType = Generator[ServiceIterTypes, ServiceSendType, None]

# endregion Service Typing

# region Service Options

ServiceSettingsTypes = str | list[str] | bool | int
ServiceSettingsDict = dict[str, ServiceSettingsTypes]
ServicesConfDictType = dict[str, ServiceSettingsDict]


class SettingFieldMetadata(TypedDict):
    pretty_name: str
    description: str
    is_deprecated: bool

# endregion Service Options


# region HelperFunctions
XDG_DESKTOP_VARS: frozenset[str] = frozenset({
    'XDG_CURRENT_DESKTOP', 'DESKTOP_SESSION',
    'XDG_SESSION_TYPE', 'XDG_SESSION_DESKTOP'})


def generate_path_var() -> str:
    """Filters PATH variable to locations with /usr prefix"""

    # Split by semicolon
    paths = environ['PATH'].split(':')
    # Filter by /usr and /tmp then join by semicolon
    return ':'.join(filter(
        lambda s: s.startswith('/usr/')
        or s == '/bin'
        or s == '/sbin',
        paths))


def generate_toolkits() -> Generator[ServiceIterTypes, None, None]:
    config_home_path = Path(BaseDirectory.xdg_config_home)
    kde_globals_conf = config_home_path / 'kdeglobals'
    if kde_globals_conf.exists():
        yield ReadOnlyBind(kde_globals_conf)

# endregion HelperFunctions


class BubblejailService:
    xdg_runtime_dir: ClassVar[Path] = Path(f"/run/user/{getuid()}")

    Settings: Type[DataclassInstance] = make_dataclass("EmptySettings", ())

    def __init__(self, context: BubblejailRunContext):
        self.context = context

    def iter_bwrap_options(self) -> ServiceGeneratorType:
        yield from ()

    async def post_init_hook(self, pid: int) -> None:
        ...

    async def post_shutdown_hook(self) -> None:
        ...

    @classmethod
    def has_settings(cls) -> bool:
        return is_dataclass(cls.Settings)

    @classmethod
    def iter_settings_fields(cls) -> Iterator[Field[Any]]:
        try:
            yield from fields(cls.Settings)
        except TypeError:
            yield from ()

    name: ClassVar[str]
    pretty_name: ClassVar[str]
    description: ClassVar[str]
    conflicts: ClassVar[frozenset[str]] = frozenset()


# Pre version 0.6.0 home bind path
OLD_HOME_BIND = Path('/home/user')


class BubblejailDefaults(BubblejailService):

    def iter_bwrap_options(self) -> ServiceGeneratorType:
        # Distro packaged libraries and binaries
        yield ReadOnlyBind('/usr')
        yield ReadOnlyBind('/opt')
        # Recreate symlinks in / or mount them read-only if its not a symlink.
        # Should be portable between distros.
        for root_path in Path('/').iterdir():
            if (
                    root_path.name.startswith('lib')  # /lib /lib64 /lib32
                    or root_path.name == 'bin'
                    or root_path.name == 'sbin'):
                if root_path.is_symlink():
                    yield Symlink(readlink(root_path), root_path)
                else:
                    yield ReadOnlyBind(root_path)

        yield ReadOnlyBind('/etc')

        # Temporary directories
        yield DirCreate('/tmp')
        yield DirCreate('/var')

        yield DirCreate(self.xdg_runtime_dir, permissions=0o700)

        # Bind pseudo home
        real_home = Path.home()
        home_path = yield ServiceWantsHomeBind()
        yield Bind(home_path, real_home)
        yield EnvrimentalVar('HOME', str(real_home))
        # Compatibility symlink
        if real_home != OLD_HOME_BIND:
            yield Symlink(real_home, OLD_HOME_BIND)

        yield ChangeDir(real_home)

        # Set environmental variables
        from getpass import getuser
        yield EnvrimentalVar('USER', getuser())
        yield EnvrimentalVar('USERNAME', getuser())
        yield EnvrimentalVar('PATH', generate_path_var())
        yield EnvrimentalVar('XDG_RUNTIME_DIR', str(self.xdg_runtime_dir))

        yield EnvrimentalVar('LANG')

        if not environ.get('BUBBLEJAIL_DISABLE_SECCOMP_DEFAULTS'):
            for blocked_syscal in (
                "bdflush", "io_pgetevents",
                "kexec_file_load", "kexec_load",
                "migrate_pages", "move_pages",
                "nfsservctl", "nice", "oldfstat",
                "oldlstat", "oldolduname", "oldstat",
                "olduname", "pciconfig_iobase", "pciconfig_read",
                "pciconfig_write", "sgetmask", "ssetmask", "swapcontext",
                "swapoff", "swapon", "sysfs", "uselib", "userfaultfd",
                "ustat", "vm86", "vm86old", "vmsplice",

                "bpf", "fanotify_init", "lookup_dcookie",
                "perf_event_open", "quotactl", "setdomainname",
                "sethostname",

                # "chroot",
                # Firefox and Chromium fails if chroot is not available

                "delete_module", "init_module",
                "finit_module", "query_module",

                "acct",

                "iopl", "ioperm",

                "settimeofday", "stime",
                "clock_settime", "clock_settime64"

                "vhangup",

            ):
                yield SeccompSyscallErrno(
                    blocked_syscal,
                    1,
                    skip_on_not_exists=True,
                )

        # Bind session socket inside the sandbox
        dbus_session_inside_path = self.xdg_runtime_dir / 'bus'
        dbus_session_outside_path = yield ServiceWantsDbusSessionBind()
        yield EnvrimentalVar(
            'DBUS_SESSION_BUS_ADDRESS',
            f"unix:path={dbus_session_inside_path}")
        yield Bind(
            dbus_session_outside_path,
            dbus_session_inside_path,
        )

    def __repr__(self) -> str:
        return "Bubblejail defaults."

    name = 'default'
    pretty_name = 'Default settings'
    description = ('Settings that must be present in any instance')


class CommonSettings(BubblejailService):

    @dataclass
    class Settings:
        executable_name: str | list[str] = field(
            default='',
            metadata=SettingFieldMetadata(
                pretty_name='Default arguments',
                description=(
                    'Default arguments to run when no arguments were provided'
                ),
                is_deprecated=False,
            )
        )
        share_local_time: bool = field(
            default=False,
            metadata=SettingFieldMetadata(
                pretty_name='Share local time',
                description='This option has no effect since version 0.6.0',
                is_deprecated=True,
            )
        )
        filter_disk_sync: bool = field(
            default=False,
            metadata=SettingFieldMetadata(
                pretty_name='Filter disk sync',
                description=(
                    'Do not allow flushing disk. '
                    'Useful for EA Origin client that tries to flush '
                    'to disk too often.'
                ),
                is_deprecated=False,
            )
        )
        dbus_name: str = field(
            default='',
            metadata=SettingFieldMetadata(
                pretty_name='Application\'s D-Bus name',
                description='D-Bus name allowed to acquire and own',
                is_deprecated=False,
            )
        )

    def iter_bwrap_options(self) -> ServiceGeneratorType:
        settings = self.context.get_settings(CommonSettings.Settings)

        # Executable main arguments
        if settings.executable_name:
            if isinstance(settings.executable_name, str):
                yield LaunchArguments([settings.executable_name])
            else:
                yield LaunchArguments(settings.executable_name)

        if settings.filter_disk_sync:
            yield SeccompSyscallErrno('sync', 0)
            yield SeccompSyscallErrno('fsync', 0)

        if dbus_name := settings.dbus_name:
            yield DbusSessionOwn(dbus_name)

    name = 'common'
    pretty_name = 'Common Settings'
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
            if x in environ:
                yield EnvrimentalVar(x)

        yield EnvrimentalVar('DISPLAY')

        if x11_socket_path := self.x11_socket_path(environ["DISPLAY"]):
            yield ReadOnlyBind(x11_socket_path)

        x_authority_path_str = environ.get('XAUTHORITY')
        if x_authority_path_str is not None:
            yield ReadOnlyBind(x_authority_path_str, '/tmp/.Xauthority')
            yield EnvrimentalVar('XAUTHORITY', '/tmp/.Xauthority')

        yield from generate_toolkits()

    name = 'x11'
    pretty_name = 'X11 windowing system'
    description = ('Gives access to X11 socket.\n'
                   'This is generally the default Linux windowing system.')


class Wayland(BubblejailService):
    def iter_bwrap_options(self) -> ServiceGeneratorType:

        try:
            wayland_display_env = environ['WAYLAND_DISPLAY']
        except KeyError:
            print("No wayland display.")

        for x in XDG_DESKTOP_VARS:
            if x in environ:
                yield EnvrimentalVar(x)

        yield EnvrimentalVar('GDK_BACKEND', 'wayland')
        yield EnvrimentalVar('MOZ_DBUS_REMOTE', '1')
        yield EnvrimentalVar('MOZ_ENABLE_WAYLAND', '1')

        yield EnvrimentalVar('WAYLAND_DISPLAY', 'wayland-0')
        original_socket_path = (Path(BaseDirectory.get_runtime_dir())
                                / wayland_display_env)

        new_socket_path = self.xdg_runtime_dir / 'wayland-0'
        yield Bind(original_socket_path, new_socket_path)
        yield from generate_toolkits()

    name = 'wayland'
    pretty_name = 'Wayland windowing system'
    description = (
        'Make sure you are running Wayland session\n'
        'and your application supports Wayland'
    )


class Network(BubblejailService):
    def iter_bwrap_options(self) -> ServiceGeneratorType:

        yield ShareNetwork()

    name = 'network'
    pretty_name = 'Network access'
    description = 'Gives access to network.'
    conflicts = frozenset(('slirp4netns', ))


class PulseAudio(BubblejailService):
    def iter_bwrap_options(self) -> ServiceGeneratorType:

        yield Bind(
            f"{BaseDirectory.get_runtime_dir()}/pulse/native",
            self.xdg_runtime_dir / 'pulse/native',
        )

    name = 'pulse_audio'
    pretty_name = 'Pulse Audio'
    description = 'Default audio system in most distros'


class HomeShare(BubblejailService):

    @dataclass
    class Settings:
        home_paths: list[str] = field(
            default_factory=list,
            metadata=SettingFieldMetadata(
                pretty_name='List of paths',
                description='Path to share with sandbox',
                is_deprecated=False,
            )
        )

    def iter_bwrap_options(self) -> ServiceGeneratorType:

        settings = self.context.get_settings(HomeShare.Settings)

        for path_relative_to_home in settings.home_paths:
            yield Bind(
                Path.home() / path_relative_to_home,
            )

    name = 'home_share'
    pretty_name = 'Home Share'
    description = 'Share directories or files relative to home'


class DirectRendering(BubblejailService):

    @dataclass
    class Settings:
        enable_aco: bool = field(
            default=False,
            metadata=SettingFieldMetadata(
                pretty_name='Enable ACO',
                description=(
                    'Enables high performance vulkan shader '
                    'compiler for AMD GPUs. Enabled by default '
                    'since mesa 20.02'
                ),
                is_deprecated=True,
            )
        )

    def iter_bwrap_options(self) -> ServiceGeneratorType:

        # TODO: Allow to select which DRM devices to pass

        # Bind /dev/dri and /sys/dev/char and /sys/devices
        # Get names of cardX and renderX in /dev/dri
        dev_dri_path = Path('/dev/dri/')
        device_names = set()
        for x in dev_dri_path.iterdir():
            if x.is_char_device():
                device_names.add(x.stem)

        # Resolve links in /sys/dev/char/
        sys_dev_char_path = Path('/sys/dev/char/')
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

        yield DevBind('/dev/dri')

        # Nvidia specific binds
        for x in Path('/dev/').iterdir():
            if x.name.startswith('nvidia'):
                yield DevBind(x)

    name = 'direct_rendering'
    pretty_name = 'Direct Rendering'
    description = 'Provides access to GPU'


class Systray(BubblejailService):
    def iter_bwrap_options(self) -> ServiceGeneratorType:
        yield DbusSessionTalkTo('org.kde.StatusNotifierWatcher')

    name = 'systray'
    pretty_name = 'System tray icons'
    description = (
        'Provides access to D-Bus API for creating tray icons\n'
        'This is not the only way to create tray icons but\n'
        'the most common one.'
    )


class Joystick(BubblejailService):
    def iter_bwrap_options(self) -> ServiceGeneratorType:
        look_for_names: set[str] = set()

        dev_input_path = Path('/dev/input')
        sys_class_input_path = Path('/sys/class/input')
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
                if input_element.name.startswith('event'):
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

    name = 'joystick'
    pretty_name = 'Joysticks and gamepads'
    description = (
        'Windowing systems (x11 and wayland) do not support gamepads.\n'
        'Every game has to read from device files directly.\n'
        'This service provides access to required '
    )


class RootShare(BubblejailService):

    @dataclass
    class Settings:
        paths: list[str] = field(
            default_factory=list,
            metadata=SettingFieldMetadata(
                pretty_name='Read/Write paths',
                description='Path to share with sandbox',
                is_deprecated=False,
            )
        )
        read_only_paths: list[str] = field(
            default_factory=list,
            metadata=SettingFieldMetadata(
                pretty_name='Read only paths',
                description='Path to share read-only with sandbox',
                is_deprecated=False,
            )
        )

    def iter_bwrap_options(self) -> ServiceGeneratorType:
        settings = self.context.get_settings(RootShare.Settings)

        for x in settings.paths:
            yield Bind(x)

        for x in settings.read_only_paths:
            yield ReadOnlyBind(x)

    name = 'root_share'
    pretty_name = 'Root share'
    description = (
        'Share directories or files relative to root /'
    )


class OpenJDK(BubblejailService):
    name = 'openjdk'
    pretty_name = 'Java'
    description = (
        'Enable for applications that require Java\n'
        'Example: Minecraft'
    )


class Notifications(BubblejailService):
    def iter_bwrap_options(self) -> ServiceGeneratorType:
        yield DbusSessionTalkTo('org.freedesktop.Notifications')

    name = 'notify'
    pretty_name = 'Notifications'
    description = 'Ability to send notifications to desktop'


class GnomeToolkit(BubblejailService):

    @dataclass
    class Settings:
        gnome_portal: bool = field(
            default=False,
            metadata=SettingFieldMetadata(
                pretty_name='GNOME Portal',
                description='Access to GNOME Portal D-Bus API',
                is_deprecated=False,
            )
        )
        dconf_dbus: bool = field(
            default=False,
            metadata=SettingFieldMetadata(
                pretty_name='Dconf D-Bus',
                description='Access to dconf D-Bus API',
                is_deprecated=False,
            )
        )
        gnome_vfs_dbus: bool = field(
            default=False,
            metadata=SettingFieldMetadata(
                pretty_name='GNOME VFS',
                description='Access to GNOME Virtual File System D-Bus API',
                is_deprecated=False,
            )
        )

    def iter_bwrap_options(self) -> ServiceGeneratorType:
        settings = self.context.get_settings(GnomeToolkit.Settings)

        if settings.gnome_portal:
            yield EnvrimentalVar('GTK_USE_PORTAL', '1')
            yield DbusSessionTalkTo('org.freedesktop.portal.*')

        if settings.dconf_dbus:
            yield DbusSessionTalkTo('ca.desrt.dconf')

        if settings.gnome_vfs_dbus:
            yield DbusSessionTalkTo('org.gtk.vfs.*')

        # TODO: org.a11y.Bus accessibility services
        # Needs both dbus and socket, socket is address is
        # acquired from dbus

    name = 'gnome_toolkit'
    pretty_name = 'GNOME toolkit'
    description = 'Access to GNOME APIs'


class Pipewire(BubblejailService):
    def iter_bwrap_options(self) -> ServiceGeneratorType:
        PIPEWIRE_SOCKET_NAME = 'pipewire-0'
        original_socket_path = (Path(BaseDirectory.get_runtime_dir())
                                / PIPEWIRE_SOCKET_NAME)

        new_socket_path = self.xdg_runtime_dir / 'pipewire-0'

        yield ReadOnlyBind(original_socket_path, new_socket_path)

    name = 'pipewire'
    pretty_name = 'Pipewire'
    description = 'Pipewire sound and screencapture system'


class VideoForLinux(BubblejailService):
    def iter_bwrap_options(self) -> ServiceGeneratorType:

        yield DevBindTry('/dev/v4l')
        yield DevBindTry('/sys/class/video4linux')
        yield DevBindTry('/sys/bus/media/')

        try:
            sys_v4l_iterator = Path('/sys/class/video4linux').iterdir()
            for sys_path in sys_v4l_iterator:
                pcie_path = sys_path.resolve()

                for char_path in Path('/sys/dev/char/').iterdir():
                    if char_path.resolve() == pcie_path:
                        yield Symlink(readlink(char_path), char_path)

                yield DevBind(pcie_path.parents[1])
        except FileNotFoundError:
            ...

        for dev_path in Path('/dev').iterdir():

            name = dev_path.name

            if not (name.startswith('video') or name.startswith('media')):
                continue

            if not name[5:].isnumeric():
                continue

            yield DevBind(dev_path)

    name = 'v4l'
    pretty_name = 'Video4Linux'
    description = 'Video capture. (webcams and etc.)'


class IBus(BubblejailService):
    def iter_bwrap_options(self) -> ServiceGeneratorType:
        yield EnvrimentalVar('IBUS_USE_PORTAL', '1')
        yield EnvrimentalVar('GTK_IM_MODULE', 'ibus')
        yield EnvrimentalVar('QT_IM_MODULE', 'ibus')
        yield EnvrimentalVar('XMODIFIERS', '@im=ibus')
        yield EnvrimentalVar('GLFW_IM_MODULE', 'ibus')
        yield DbusSessionTalkTo('org.freedesktop.portal.IBus.*')

    name = 'ibus'
    pretty_name = 'IBus input method'
    description = (
        'Gives access to IBus input method.\n'
        'This is generally the default input method for multilingual input.'
    )
    conflicts = frozenset(('fcitx', ))


class Fcitx(BubblejailService):

    def iter_bwrap_options(self) -> ServiceGeneratorType:
        yield EnvrimentalVar('GTK_IM_MODULE', 'fcitx')
        yield EnvrimentalVar('QT_IM_MODULE', 'fcitx')
        yield EnvrimentalVar('XMODIFIERS', '@im=fcitx')
        yield EnvrimentalVar('SDL_IM_MODULE', 'fcitx')
        yield EnvrimentalVar('GLFW_IM_MODULE', 'ibus')
        yield DbusSessionTalkTo('org.freedesktop.portal.Fcitx.*')
        yield DbusSessionTalkTo('org.freedesktop.portal.IBus.*')

    name = 'fcitx'
    pretty_name = 'Fcitx/Fcitx5 input method'
    description = (
        'Gives access to Fcitx/Fcitx5 input method.\n'
        'This is another popular input method framework.'
    )
    conflicts = frozenset(('ibus', ))


class Slirp4netns(BubblejailService):

    @dataclass
    class Settings:
        dns_servers: list[str] = field(
            default_factory=list,
            metadata=SettingFieldMetadata(
                pretty_name='DNS servers',
                description=(
                    'DNS servers used. '
                    'Internal DNS server is always used.'
                ),
                is_deprecated=False,
            )
        )
        outbound_addr: str = field(
            default='',
            metadata=SettingFieldMetadata(
                pretty_name='Outbound address or deivce',
                description=(
                    'Address or device to bind to. '
                    'If not set the default address would be used.'
                ),
                is_deprecated=False,
            )
        )
        disable_host_loopback: bool = field(
            default=True,
            metadata=SettingFieldMetadata(
                pretty_name='Disable host loopback access',
                description=(
                    'Prohibit connecting to host\'s loopback interface'
                ),
                is_deprecated=False,
            )
        )

    def __init__(self, context: BubblejailRunContext) -> None:
        super().__init__(context)
        self.slirp_process: AsyncioProcess | None = None

    def iter_bwrap_options(self) -> ServiceGeneratorType:
        settings = self.context.get_settings(Slirp4netns.Settings)

        self.outbound_addr = settings.outbound_addr
        self.disable_host_loopback = settings.disable_host_loopback

        if machine() != 'x86_64':
            raise NotImplementedError('Slirp4netns only available on x86_64')

        dns_servers = settings.dns_servers.copy()
        dns_servers.append("10.0.2.3")

        yield FileTransfer(
            b"\n".join(
                f"nameserver {x}".encode()
                for x in dns_servers
            ),
            '/etc/resolv.conf'
        )

    async def post_init_hook(self, pid: int) -> None:
        settings = self.context.get_settings(Slirp4netns.Settings)

        outbound_addr = settings.outbound_addr
        disable_host_loopback = settings.disable_host_loopback

        from bubblejail.namespaces import UserNamespace
        target_namespace = UserNamespace.from_pid(pid)
        parent_ns = target_namespace.get_parent_ns()
        parent_ns_fd = parent_ns._fd
        parent_ns_path = f"/proc/{getpid()}/fd/{parent_ns_fd}"

        ready_pipe_read, ready_pipe_write = (
            pipe2(O_NONBLOCK | O_CLOEXEC)
        )

        loop = get_running_loop()
        slirp_ready_event = Event()
        loop.add_reader(ready_pipe_read, slirp_ready_event.set)

        slirp_bin_path = which("slirp4netns")
        if not slirp_bin_path:
            raise BubblejailDependencyError("slirp4netns binary not found")

        slirp4netns_args = [
            slirp_bin_path,
            f"--ready={ready_pipe_write}",
            '--configure',
            f"--userns-path={parent_ns_path}",
        ]

        if outbound_addr:
            slirp4netns_args.append(
                (f"--outbound-addr={outbound_addr}")
            )

        if disable_host_loopback:
            slirp4netns_args.append('--disable-host-loopback')

        slirp4netns_args.append(str(pid))
        slirp4netns_args.append('tap0')

        self.slirp_process = await create_subprocess_exec(
            *slirp4netns_args,
            pass_fds=[ready_pipe_write],
        )

        slirp_ready_task = loop.create_task(
            slirp_ready_event.wait(),
            name="slirp4netns ready",
        )

        early_process_end_task = loop.create_task(
            self.slirp_process.wait(),
            name="Early slirp4netns process end"
        )
        early_process_end_task.add_done_callback(
            lambda _: slirp_ready_task.cancel()
        )

        try:
            await wait_for(slirp_ready_task, timeout=3)
        except CancelledError:
            raise BubblejailInitializationError(
                "Slirp4netns initialization failed"
            )
        finally:
            loop.remove_reader(ready_pipe_read)
            early_process_end_task.cancel()

        with open(ready_pipe_write), open(ready_pipe_read) as f:
            f.read()

    async def post_shutdown_hook(self) -> None:
        try:
            if self.slirp_process is not None:
                self.slirp_process.terminate()
                await wait_for(self.slirp_process.wait(), timeout=3)
        except ProcessLookupError:
            ...

    name = 'slirp4netns'
    pretty_name = 'Slirp4netns networking'
    description = (
        "Independent networking stack for sandbox. "
        "Requires slirp4netns executable."
    )
    conflicts = frozenset(('network', ))


class NamespacesLimits(BubblejailService):

    @dataclass
    class Settings:
        user: int = field(
            default=0,
            metadata=SettingFieldMetadata(
                pretty_name='Max number of user namespaces',
                description=(
                    'Limiting user namespaces blocks acquiring new '
                    'capabilities and privileges inside namespaces.'
                ),
                is_deprecated=False,
            )
        )
        mount: int = field(
            default=0,
            metadata=SettingFieldMetadata(
                pretty_name='Max number of mount namespaces',
                description=(
                    'Limits number mount namespaces.'
                ),
                is_deprecated=False,
            )
        )
        pid: int = field(
            default=0,
            metadata=SettingFieldMetadata(
                pretty_name='Max number of PID namespaces',
                description=(
                    'Limits number PID namespaces.'
                ),
                is_deprecated=False,
            )
        )
        ipc: int = field(
            default=0,
            metadata=SettingFieldMetadata(
                pretty_name='Max number of IPC namespaces',
                description=(
                    'Limits number IPC namespaces.'
                ),
                is_deprecated=False,
            )
        )
        net: int = field(
            default=0,
            metadata=SettingFieldMetadata(
                pretty_name='Max number of net namespaces',
                description=(
                    'Limits number net namespaces.'
                ),
                is_deprecated=False,
            )
        )
        time: int = field(
            default=0,
            metadata=SettingFieldMetadata(
                pretty_name='Max number of time namespaces',
                description=(
                    'Limits number time namespaces.'
                ),
                is_deprecated=False,
            )
        )
        uts: int = field(
            default=0,
            metadata=SettingFieldMetadata(
                pretty_name='Max number of UTS namespaces',
                description=(
                    'Limits number UTS namespaces.'
                ),
                is_deprecated=False,
            )
        )
        cgroup: int = field(
            default=0,
            metadata=SettingFieldMetadata(
                pretty_name='Max number of cgroups namespaces',
                description=(
                    'Limits number cgroups namespaces.'
                ),
                is_deprecated=False,
            )
        )

    def iter_bwrap_options(self) -> ServiceGeneratorType:
        if machine() != 'x86_64':
            raise NotImplementedError('Limit namespaces only available on x86_64')

        yield from ()

    @staticmethod
    def set_namespaces_limits(
        pid: int,
        namespace_files_to_limits: dict[str, int],
    ) -> None:
        from bubblejail.namespaces import UserNamespace
        target_namespace = UserNamespace.from_pid(pid)
        parent_ns = target_namespace.get_parent_ns()
        parent_ns.setns()

        for proc_file, limit_to_set in namespace_files_to_limits.items():
            with open("/proc/sys/user/" + proc_file, mode="w") as f:
                f.write(str(limit_to_set))

    async def post_init_hook(self, pid: int) -> None:
        settings = self.context.get_settings(NamespacesLimits.Settings)

        namespace_files_to_limits: dict[str, int] = {}
        if (user_ns_limit := settings.user) >= 0:
            namespace_files_to_limits["max_user_namespaces"] = (
                user_ns_limit and user_ns_limit + 1)

        if (mount_ns_limit := settings.mount) >= 0:
            namespace_files_to_limits["max_mnt_namespaces"] = (
                mount_ns_limit and mount_ns_limit + 1)

        if (pid_ns_limit := settings.pid) >= 0:
            namespace_files_to_limits["max_pid_namespaces"] = (
                pid_ns_limit and pid_ns_limit + 1)

        if (ipc_ns_limit := settings.ipc) >= 0:
            namespace_files_to_limits["max_ipc_namespaces"] = (
                ipc_ns_limit and ipc_ns_limit + 1)

        if (net_ns_limit := settings.net) >= 0:
            if not self.context.is_service_enabled(Network):
                net_ns_limit += 1

            namespace_files_to_limits["max_net_namespaces"] = net_ns_limit

        if (time_ns_limit := settings.time) >= 0:
            namespace_files_to_limits["max_time_namespaces"] = time_ns_limit

        if (uts_ns_limit := settings.uts) >= 0:
            namespace_files_to_limits["max_uts_namespaces"] = (
                uts_ns_limit and uts_ns_limit + 1)

        if (cgroup_ns_limit := settings.cgroup) >= 0:
            namespace_files_to_limits["max_cgroup_namespaces"] = (
                cgroup_ns_limit and cgroup_ns_limit + 1)

        setter_process = Process(
            target=self.set_namespaces_limits,
            args=(pid, namespace_files_to_limits)
        )
        setter_process.start()
        setter_process.join(3)
        setter_process.close()

    name = "namespaces_limits"
    pretty_name = "Limit namespaces"
    description = (
        "Limit number of namespaces available inside sandbox. "
        "Namespace limits are recursive. Setting limit 0 blocks "
        "creating new namespaces. Setting -1 unlocks the limit."
    )


SERVICES_CLASSES: tuple[Type[BubblejailService], ...] = (
    CommonSettings, X11, Wayland,
    Network, PulseAudio, HomeShare, DirectRendering,
    Systray, Joystick, RootShare, OpenJDK, Notifications,
    GnomeToolkit, Pipewire, VideoForLinux, IBus, Fcitx,
    Slirp4netns, NamespacesLimits,
)

SERVICES_MAP: dict[str, Type[BubblejailService]] = {
    service.name: service for service in SERVICES_CLASSES
}


if TYPE_CHECKING:
    T = TypeVar('T', bound="object")


class BubblejailRunContext:
    def __init__(
        self,
        services: dict[str, BubblejailService],
        services_to_type_dict: dict[Type[T], T],
    ):
        self.services = services
        self.services_to_type_dict = services_to_type_dict

    def get_settings(self, settings_type: Type[T]) -> T:
        return self.services_to_type_dict[settings_type]

    def is_service_enabled(
        self,
        service_type: Type[BubblejailService],
    ) -> bool:
        return service_type.name in self.services


class ServiceContainer:
    def __init__(self, conf_dict: ServicesConfDictType | None = None):
        self.service_settings_to_type: dict[Type[Any], Any] = {}
        self.service_settings: dict[str, DataclassInstance] = {}
        self.services: dict[str, BubblejailService] = {}
        self.context = BubblejailRunContext(
            self.services,
            self.service_settings_to_type,
        )
        self.default_service = BubblejailDefaults(self.context)

        if conf_dict is not None:
            self.set_services(conf_dict)

    def set_services(
            self,
            new_services_datas: ServicesConfDictType) -> None:

        declared_services: set[str] = set()
        self.services.clear()
        self.service_settings.clear()
        self.service_settings_to_type.clear()

        for service_name, service_options_dict in new_services_datas.items():
            service_class = SERVICES_MAP[service_name]
            service_settings_class = service_class.Settings

            self.services[service_name] = service_class(self.context)

            service_settings = service_settings_class(**service_options_dict)

            self.service_settings_to_type[service_settings_class] = (
                service_settings
            )
            self.service_settings[service_name] = service_settings

            declared_services.add(service_name)

            if conflicting_services := (
                    declared_services & service_class.conflicts):
                raise ServiceConflictError(
                    f"Service conflict between {service_name} and "
                    f"{', '.join(conflicting_services)}"
                )

    def get_service_conf_dict(self) -> ServicesConfDictType:
        new_dict: ServicesConfDictType = {}

        for k, v in self.service_settings.items():
            try:
                new_dict[k] = asdict(v)
            except TypeError:
                new_dict[k] = {}

        return new_dict

    def iter_services(
        self,
        iter_default: bool = True,
    ) -> Iterator[BubblejailService]:

        if iter_default:
            yield self.default_service

        yield from self.services.values()

    def iter_post_init_hooks(
        self
    ) -> Iterator[Callable[[int], Awaitable[None]]]:
        for service in self.services.values():
            if (service.__class__.post_init_hook
               is BubblejailService.post_init_hook):
                continue

            yield service.post_init_hook

    def iter_post_shutdown_hooks(
        self
    ) -> Iterator[Callable[[], Awaitable[None]]]:
        for service in self.services.values():
            if (service.__class__.post_shutdown_hook
               is BubblejailService.post_shutdown_hook):
                continue

            yield service.post_shutdown_hook
