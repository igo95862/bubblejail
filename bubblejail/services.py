# SPDX-License-Identifier: GPL-3.0-or-later

# Copyright 2019, 2020 igo95862

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


from dataclasses import dataclass
from os import environ, readlink
from pathlib import Path
from random import choices
from string import ascii_letters, hexdigits
from typing import (Dict, FrozenSet, Generator, List, Optional, Set, Tuple,
                    Type, Union)

from xdg import BaseDirectory

from .bwrap_config import (Bind, BwrapConfigBase, DbusSessionTalkTo, DevBind,
                           DirCreate, EnvrimentalVar, FileTransfer,
                           ReadOnlyBind, SeccompDirective, SeccompSyscallErrno,
                           ShareNetwork, Symlink)
from .exceptions import ServiceUnavalibleError

ServiceIterTypes = Union[BwrapConfigBase, FileTransfer,
                         DbusSessionTalkTo, SeccompDirective]

# region ServiceInfo

ServiceOptionTypes = Union[Type[str], Type[bool], Type[List[str]]]


@dataclass
class ServiceOptionInfo:
    name: str
    description: str
    typing: ServiceOptionTypes


@dataclass
class ServiceInfo:
    name: str
    description: str
    options: Dict[str, ServiceOptionInfo]


# endregion ServiceInfo


# region HelperFunctions

XDG_DESKTOP_VARS: FrozenSet[str] = frozenset({
    'XDG_CURRENT_DESKTOP', 'DESKTOP_SESSION',
    'XDG_SESSION_TYPE', 'XDG_SESSION_DESKTOP'})


def generate_path_var() -> str:
    """Filters PATH variable to locations with /usr prefix"""

    # Split by semicolon
    paths = environ['PATH'].split(':')
    # Filter by /usr and /tmp then join by semicolon
    return ':'.join(filter(
        lambda s: s.startswith('/usr/') or s.startswith('/tmp/'),
        paths))


def generate_passwd() -> FileTransfer:
    passwd = '\n'.join((
        'root:x:0:0::/root:/bin/nologin',
        'user:x:1000:1000::/home/user:/bin/nologin',
        'nobody:x:65534:65534:Nobody:/:/usr/bin/nologin',
    ))

    return FileTransfer(passwd.encode(), '/etc/passwd')


def generate_group() -> FileTransfer:
    group = '\n'.join((
        'root:x:0:root',
        'user:x:1000:user',
        'nobody:x:65534:',
    ))

    return FileTransfer(group.encode(), '/etc/group')


def generate_nssswitch() -> FileTransfer:
    """
    Based on what Arch Linux packages by default

    Disables some systemd stuff that we don't need in sandbox
    """

    nsswitch = '''passwd: files
group: files
shadow: files

publickey: files

hosts: files myhostname dns
networks: files

protocols: files
services: files
ethers: files
rpc: files

netgroup: files'''
    return FileTransfer(nsswitch.encode(), '/etc/nsswitch.conf')


def random_hostname() -> str:
    random_hostname = choices(
        population=ascii_letters,
        k=10,
    )
    return ''.join(random_hostname)


def generate_hosts() -> Tuple[FileTransfer, FileTransfer]:
    hostname = random_hostname()
    hosts = '\n'.join((
        '127.0.0.1               localhost',
        '::1                     localhost',
        f'127.0.1.1               {hostname}.localdomain {hostname}',
    ))
    return (FileTransfer(hostname.encode(), '/etc/hostname'),
            FileTransfer(hosts.encode(), '/etc/hosts'))


def generate_toolkits() -> Generator[ServiceIterTypes, None, None]:
    config_home_path = Path(BaseDirectory.xdg_config_home)
    kde_globals_conf = config_home_path / 'kdeglobals'
    if kde_globals_conf.exists():
        yield ReadOnlyBind(
            str(kde_globals_conf),
            '/home/user/.config/kdeglobals')


def generate_machine_id_bytes() -> bytes:
    random_hex_string = choices(
        population=hexdigits.lower(),
        k=32,
    )

    return b''.join((x.encode() for x in random_hex_string))

# endregion HelperFunctions


# HACK: makes typing easier rather than None
EMPTY_LIST: List[str] = []


class BubblejailService:

    def __iter__(self) -> Generator[ServiceIterTypes, None, None]:
        raise NotImplementedError('Default iterator was called')

    info: Optional[ServiceInfo] = None


class BubblejailDefaults(BubblejailService):

    def __init__(
        self,
        home_bind_path: Path,
        share_local_time: bool,
        filter_disk_sync: bool,
    ) -> None:
        super().__init__()
        self.home_bind_path = home_bind_path
        self.share_local_time = share_local_time
        self.filter_disk_sync = filter_disk_sync

    def __iter__(self) -> Generator[ServiceIterTypes, None, None]:
        # Distro packged libraries and binaries
        yield ReadOnlyBind('/usr/include')
        yield ReadOnlyBind('/usr/bin')
        yield ReadOnlyBind('/usr/lib')
        yield ReadOnlyBind('/usr/lib32')
        yield ReadOnlyBind('/usr/share')
        yield ReadOnlyBind('/usr/src')
        yield ReadOnlyBind('/opt')
        # Symlinks for /usr merge
        # Arch Linux does not separate sbin from bin unlike Debian
        # PS: why does debian do that? I can't run usermod --help
        #  to quickly check the arguments
        # Some distros do not use /usr merge
        yield Symlink('/usr/lib', '/lib')
        yield Symlink('/usr/lib64', '/lib64')
        yield Symlink('/usr/bin', '/bin')
        yield Symlink('/usr/sbin', '/sbin')
        yield Symlink('/usr/lib', '/usr/lib64')
        yield Symlink('/usr/bin', '/usr/sbin')

        # yield ReadOnlyBind('/etc/resolv.conf'),
        yield ReadOnlyBind('/etc/login.defs')  # ???: is this file needed
        # ldconfig: linker cache
        # particulary needed for steam runtime to work
        yield ReadOnlyBind('/etc/ld.so.cache')
        yield ReadOnlyBind('/etc/ld.so.conf')
        yield ReadOnlyBind('/etc/ld.so.conf.d')

        # Temporary directories
        yield DirCreate('/tmp')
        yield DirCreate('/var')

        yield DirCreate('/run/user/1000')
        yield DirCreate('/usr/local')  # Used for overwrites

        # Bind pseudo home
        yield Bind(str(self.home_bind_path), '/home/user')

        # Set enviromental variables
        yield EnvrimentalVar('USER', 'user')
        yield EnvrimentalVar('USERNAME', 'user')
        yield EnvrimentalVar('HOME', '/home/user')
        yield EnvrimentalVar('PATH', generate_path_var())
        yield EnvrimentalVar('XDG_RUNTIME_DIR', '/run/user/1000')

        yield EnvrimentalVar('LANG')

        yield generate_passwd()
        yield generate_group()
        yield generate_nssswitch()
        yield FileTransfer(b'multi on', '/etc/host.conf')
        yield from generate_hosts()
        if self.share_local_time:
            yield ReadOnlyBind('/etc/localtime')

        yield FileTransfer(generate_machine_id_bytes(), '/etc/machine-id')

        if self.filter_disk_sync:
            yield SeccompSyscallErrno('sync', 0)
            yield SeccompSyscallErrno('fsync', 0)

    info = ServiceInfo(
        name='Default settings',
        description=('Settings that must be present in any instance'),
        options={
            'executable_name': ServiceOptionInfo(
                name='Executable arguments',
                description='Space separated arguments',
                typing=str,
            ),
            'share_local_time': ServiceOptionInfo(
                name='Share local time',
                description=(
                    'Instance will know local time instead of UTC'
                ),
                typing=bool,
            ),
            'filter_disk_sync': ServiceOptionInfo(
                name='Filter disk sync',
                description=(
                    'Do not allow flushing disk\n'
                    'Useful for EA Origin client that tries to flush\n'
                    'to disk too often.'
                ),
                typing=bool,
            ),
        },
    )


class X11(BubblejailService):
    def __iter__(self) -> Generator[ServiceIterTypes, None, None]:
        for x in XDG_DESKTOP_VARS:
            if x in environ:
                yield EnvrimentalVar(x)

        yield EnvrimentalVar('DISPLAY')
        yield Bind(f"/tmp/.X11-unix/X{environ['DISPLAY'][1:]}")
        yield ReadOnlyBind(environ['XAUTHORITY'], '/tmp/.Xauthority')
        yield ReadOnlyBind('/etc/fonts')
        yield EnvrimentalVar('XAUTHORITY', '/tmp/.Xauthority')
        yield from generate_toolkits()

    info = ServiceInfo(
        name='X11 windowing system',
        description=('Gives access to X11 socket.\n'
                     'This is generally the default Linux windowing system.'),
        options={},
    )


class Wayland(BubblejailService):
    def __iter__(self) -> Generator[ServiceIterTypes, None, None]:
        if 'WAYLAND_DISPLAY' not in environ:
            raise ServiceUnavalibleError("No wayland display.")

        for x in XDG_DESKTOP_VARS:
            if x in environ:
                yield EnvrimentalVar(x)

        yield EnvrimentalVar('WAYLAND_DISPLAY')
        yield EnvrimentalVar('GDK_BACKEND', 'wayland')
        yield Bind((
            f"{BaseDirectory.get_runtime_dir()}"
            f"/{environ.get('WAYLAND_DISPLAY')}"))
        yield from generate_toolkits()

    info = ServiceInfo(
        name='Wayland windowing system',
        description=(
            'Make sure you are running Wayland sessiion\n'
            'and your application supports Wayland'
        ),
        options={},
    )


class Network(BubblejailService):
    def __iter__(self) -> Generator[ServiceIterTypes, None, None]:
        yield ShareNetwork()
        yield ReadOnlyBind('/etc/resolv.conf')
        yield ReadOnlyBind('/etc/ca-certificates')
        yield ReadOnlyBind('/etc/ssl')

    info = ServiceInfo(
        name='Network access',
        description='Gives access to network.',
        options={},
    )


class PulseAudio(BubblejailService):
    def __iter__(self) -> Generator[ServiceIterTypes, None, None]:
        yield Bind(
            f"{BaseDirectory.get_runtime_dir()}/pulse/native",
            '/run/user/1000/pulse/native'
        )
        yield Symlink('/usr/bin/true', '/usr/local/bin/pulseaudio')

    info = ServiceInfo(
        name='Pulse Audio',
        description='Default audio system in most distros',
        options={},
    )


class HomeShare(BubblejailService):
    def __init__(self, home_paths: List[str] = EMPTY_LIST):
        super().__init__()
        self.home_paths = home_paths

    def __iter__(self) -> Generator[ServiceIterTypes, None, None]:
        if self.home_paths is not None:
            for path_relative_to_home in self.home_paths:
                yield Bind(
                    str(Path.home() / path_relative_to_home),
                    str(Path('/home/user') / path_relative_to_home),
                )

    info = ServiceInfo(
        name='Home Share',
        description='Share directories relative to home',
        options={
            'home_paths': ServiceOptionInfo(
                name='List of paths',
                description='Add directory name and path to share',
                typing=List[str],
            )
        }
    )


class DirectRendering(BubblejailService):
    def __init__(self, enable_aco: bool = False):
        super().__init__()
        self.enable_aco = enable_aco

    def __iter__(self) -> Generator[ServiceIterTypes, None, None]:
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
                yield Symlink(str(x_resolved), str(x))
                # Add the two times parent (parents[1])
                # Seems like the dri devices are stored as
                # /sys/devices/..pcie_id../drm/dri
                # We want to bind the /sys/devices/..pcie_id../
                yield DevBind(str(x_resolved.parents[1]))

        yield DevBind('/dev/dri')

        if self.enable_aco:
            yield EnvrimentalVar('RADV_PERFTEST', 'aco')

    info = ServiceInfo(
        name='Direct Rendering',
        description='Provides ccess to GPU',
        options={
            'enable_aco': ServiceOptionInfo(
                name='Enable ACO',
                description=(
                    'Enables high performance vulkan shader\n'
                    'compiler for AMD GPUs. No effect on Nvidia\n'
                    'or Intel.'
                ),
                typing=bool,
            )
        },
    )


class Systray(BubblejailService):
    def __iter__(self) -> Generator[ServiceIterTypes, None, None]:
        yield DbusSessionTalkTo('org.kde.StatusNotifierWatcher')

    info = ServiceInfo(
        name='System tray icons',
        description=(
            'Provides access to Dbus API for creating tray icons\n'
            'This is not the only way to create tray icons but\n'
            'the most common one.'
        ),
        options={},
    )


class Joystick(BubblejailService):
    def __iter__(self) -> Generator[ServiceIterTypes, None, None]:
        look_for_names: Set[str] = set()
        # Find the *-joystick in /dev/input/by-path/
        dev_input_path = Path('/dev/input')
        for x in (dev_input_path / 'by-path').iterdir():
            name = x.name
            if name.split('-')[-1] == 'joystick':
                # Add both symlink and device it self
                joystick_dev_path = x.resolve()
                look_for_names.add(joystick_dev_path.name)
                yield DevBind(str(joystick_dev_path))
                yield Symlink(str(joystick_dev_path), str(x))

        # Add device under /sys/ and a symlink from /sys/class/input
        for sys_class_input_symlink in Path('/sys/class/input').iterdir():
            if sys_class_input_symlink.name in look_for_names:
                resolved_path = sys_class_input_symlink.resolve()
                yield Symlink(
                    str(readlink(sys_class_input_symlink)),
                    str(sys_class_input_symlink)
                )

                yield DevBind(str(resolved_path.parents[2]))

    info = ServiceInfo(
        name='Joysticks and gamepads',
        description=(
            'Windowing systems (x11 and wayland) do not support gamepads.\n'
            'Every game has to read from device files directly.\n'
            'This service provides access to required '
        ),
        options={},
    )


class RootShare(BubblejailService):
    def __init__(self,
                 paths: List[str] = EMPTY_LIST,
                 read_only_paths: List[str] = EMPTY_LIST):
        super().__init__()
        if paths is not None:
            self.paths = paths
        else:
            self.paths = []

        if read_only_paths is not None:
            self.read_only_paths = read_only_paths
        else:
            self.read_only_paths = []

    def __iter__(self) -> Generator[ServiceIterTypes, None, None]:
        for x in self.paths:
            yield Bind(x)

        for x in self.read_only_paths:
            yield ReadOnlyBind(x)

    info = ServiceInfo(
        name='Root share',
        description=(
            'Share directory relative to root /'
        ),
        options={
            'paths': ServiceOptionInfo(
                name='Read/Write paths',
                description='Add directory path to share',
                typing=List[str],
            ),
            'read_only_paths': ServiceOptionInfo(
                name='Read only paths',
                description='Add directory path to share',
                typing=List[str],
            )
        },
    )


class OpenJDK(BubblejailService):
    def __iter__(self) -> Generator[ServiceIterTypes, None, None]:
        yield ReadOnlyBind('/etc/java-openjdk')
        yield ReadOnlyBind('/etc/profile.d/jre.csh')
        yield ReadOnlyBind('/etc/profile.d/jre.sh')

    info = ServiceInfo(
        name='Java',
        description=(
            'Enable for applications that require Java\n'
            'Example: Minecraft'
        ),
        options={},
    )


class Notifications(BubblejailService):
    def __iter__(self) -> Generator[ServiceIterTypes, None, None]:
        yield DbusSessionTalkTo('org.freedesktop.Notifications')

    info = ServiceInfo(
        name='Notifications',
        description='Ability to send notifications to desktop',
        options={},
    )


SERVICES: Dict[str, Type[BubblejailService]] = {
    'default': BubblejailDefaults,
    'x11': X11,
    'wayland': Wayland,
    'network': Network,
    'pulse_audio': PulseAudio,
    'home_share': HomeShare,
    'direct_rendering': DirectRendering,
    'systray': Systray,
    'joystick': Joystick,
    'root_share': RootShare,
    'openjdk': OpenJDK,
    'notify': Notifications,
}
