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


from os import environ, readlink
from pathlib import Path
from random import choices
from string import ascii_letters, hexdigits
from typing import (Dict, FrozenSet, Generator, List, Set, Tuple,
                    Type, Union, Optional,
                    Iterator)


from xdg import BaseDirectory

from .bwrap_config import (Bind, BwrapConfigBase, DbusSessionTalkTo, DevBind,
                           DirCreate, EnvrimentalVar, FileTransfer,
                           ReadOnlyBind, SeccompDirective, SeccompSyscallErrno,
                           ShareNetwork, Symlink, LaunchArguments)
from .exceptions import ServiceUnavalibleError

# region Service Typing


class ServiceWantsSend:
    ...


class ServiceWantsHomeBind(ServiceWantsSend):
    ...


ServiceIterTypes = Union[BwrapConfigBase, FileTransfer,
                         DbusSessionTalkTo, SeccompDirective,
                         LaunchArguments, ServiceWantsSend]

ServiceSendType = Union[Path]

ServiceGeneratorType = Generator[ServiceIterTypes, ServiceSendType, None]

# endregion Service Typing

# region Service Options

ServiceOptionTypes = Union[str, List[str], bool]


class ServiceOption:
    def __init__(self, name: str, description: str, pretty_name: str):
        self.name = name
        self.description = description
        self.pretty_name = pretty_name

    def get_value(self) -> ServiceOptionTypes:
        raise NotImplementedError('Default option value getter called')

    def get_gui_value(self) -> ServiceOptionTypes:
        return self.get_value()

    def set_value(self, new_value: ServiceOptionTypes) -> None:
        raise NotImplementedError('Default option value setter called')


class OptionStrList(ServiceOption):
    def __init__(self, str_list: List[str],
                 description: str, name: str,
                 pretty_name: str):
        super().__init__(
            description=description,
            name=name,
            pretty_name=pretty_name,
        )
        self.str_list = str_list

    def get_value(self) -> List[str]:
        return self.str_list

    def set_value(self, new_value: ServiceOptionTypes) -> None:
        if isinstance(new_value, list):
            self.str_list = new_value
        else:
            raise TypeError(f"Option StrList got {type(new_value)}")


class OptionSpaceSeparatedStr(OptionStrList):
    def __init__(self, str_or_list_str: Union[str, List[str]],
                 description: str, name: str,
                 pretty_name: str):

        if isinstance(str_or_list_str, str):
            str_list = str_or_list_str.split()
        elif isinstance(str_or_list_str, list):
            str_list = str_or_list_str
        else:
            raise TypeError(("Init of space separated got "
                             f"{repr(str_or_list_str)}"))

        super().__init__(
            description=description,
            name=name,
            pretty_name=pretty_name,
            str_list=str_list,
        )

    def get_gui_value(self) -> str:
        return '\t'.join(self.str_list)

    def set_value(self, new_value: ServiceOptionTypes) -> None:
        if isinstance(new_value, str):
            str_list = new_value.split()
        elif isinstance(new_value, list):
            str_list = new_value
        else:
            raise TypeError(f"Option space separated got {type(new_value)}")

        super().set_value(str_list)


class OptionStr(ServiceOption):
    def __init__(self, string: str,
                 description: str, name: str,
                 pretty_name: str):
        super().__init__(
            description=description,
            name=name,
            pretty_name=pretty_name,
        )
        self.string = string

    def get_value(self) -> str:
        return self.string

    def set_value(self, new_value: ServiceOptionTypes) -> None:
        if isinstance(new_value, str):
            self.string = new_value
        else:
            raise TypeError(f"Option Str got {type(new_value)}")


class OptionBool(ServiceOption):
    def __init__(self, boolean: bool,
                 description: str, name: str,
                 pretty_name: str):
        super().__init__(
            description=description,
            name=name,
            pretty_name=pretty_name,
        )
        self.boolean = boolean

    def get_value(self) -> bool:
        return self.boolean

    def set_value(self, new_value: ServiceOptionTypes) -> None:
        if isinstance(new_value, bool):
            self.boolean = new_value
        else:
            raise TypeError(f"Option Bool got {type(new_value)}")

# endregion Service Options


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

    def __init__(self) -> None:
        self.option_list: List[ServiceOption] = []
        self.enabled: bool = False

    def __iter__(self) -> ServiceGeneratorType:
        if not self.enabled:
            return

        if False:
            yield None

    def add_option(self, option: ServiceOption) -> None:
        self.option_list.append(option)

    def iter_options(self) -> Iterator[ServiceOption]:
        return iter(self.option_list)

    def set_options(self, options_map: Dict[str, ServiceOptionTypes]) -> None:
        for option in self.iter_options():
            option_name = option.name
            try:
                option_new_value = options_map.pop(option_name)
            except KeyError:
                continue
            option.set_value(option_new_value)

        if options_map:
            raise TypeError(f"Unknown options {options_map}")

    def to_dict(self) -> Dict[str, ServiceOptionTypes]:
        new_dict = {}

        for option in self.iter_options():
            new_dict[option.name] = option.get_value()

        return new_dict

    name: str
    pretty_name: str
    description: str


class BubblejailDefaults(BubblejailService):

    def __iter__(self) -> ServiceGeneratorType:
        # Defaults can't be disabled

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
        home_path = yield ServiceWantsHomeBind()
        yield Bind(str(home_path), '/home/user')

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

        yield FileTransfer(generate_machine_id_bytes(), '/etc/machine-id')

    def __repr__(self) -> str:
        return "Bubblejail defaults."

    name = 'default'
    pretty_name = 'Default settings'
    description = ('Settings that must be present in any instance')


class CommonSettings(BubblejailService):
    def __init__(
        self,
        executable_name: Union[str, List[str]] = EMPTY_LIST,
        share_local_time: bool = True,
        filter_disk_sync: bool = False,
    ):
        super().__init__()
        self.share_local_time = OptionBool(
            boolean=share_local_time,
            name='share_local_time',
            pretty_name='Share local time',
            description='Instance will know local time instead of UTC',
        )

        self.filter_disk_sync = OptionBool(
            boolean=filter_disk_sync,
            name='filter_disk_sync',
            pretty_name='Filter disk sync',
            description=(
                'Do not allow flushing disk\n'
                'Useful for EA Origin client that tries to flush\n'
                'to disk too often.'),
        )

        self.executable_name = OptionSpaceSeparatedStr(
            str_or_list_str=executable_name,
            name='executable_name',
            pretty_name='Executable arguments',
            description='Space separated arguments',
        )

        self.add_option(self.executable_name)
        self.add_option(self.filter_disk_sync)
        self.add_option(self.share_local_time)

    def __iter__(self) -> ServiceGeneratorType:
        if not self.enabled:
            return

        # Executable main arguments
        yield LaunchArguments(self.executable_name.get_value())

        if self.filter_disk_sync.get_value():
            yield SeccompSyscallErrno('sync', 0)
            yield SeccompSyscallErrno('fsync', 0)

        if self.share_local_time.get_value():
            yield ReadOnlyBind('/etc/localtime')

    name = 'common'
    pretty_name = 'Common Settings'
    description = "Settins that don't fit any particular category"


class X11(BubblejailService):
    def __iter__(self) -> ServiceGeneratorType:
        if not self.enabled:
            return

        for x in XDG_DESKTOP_VARS:
            if x in environ:
                yield EnvrimentalVar(x)

        yield EnvrimentalVar('DISPLAY')
        yield Bind(f"/tmp/.X11-unix/X{environ['DISPLAY'][1:]}")
        yield ReadOnlyBind(environ['XAUTHORITY'], '/tmp/.Xauthority')
        yield ReadOnlyBind('/etc/fonts')
        yield EnvrimentalVar('XAUTHORITY', '/tmp/.Xauthority')
        yield from generate_toolkits()

    name = 'x11'
    pretty_name = 'X11 windowing system'
    description = ('Gives access to X11 socket.\n'
                   'This is generally the default Linux windowing system.')


class Wayland(BubblejailService):
    def __iter__(self) -> ServiceGeneratorType:
        if not self.enabled:
            return

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

    name = 'wayland'
    pretty_name = 'Wayland windowing system'
    description = (
        'Make sure you are running Wayland sessiion\n'
        'and your application supports Wayland'
    )


class Network(BubblejailService):
    def __iter__(self) -> ServiceGeneratorType:
        if not self.enabled:
            return

        yield ShareNetwork()
        yield ReadOnlyBind('/etc/resolv.conf')
        yield ReadOnlyBind('/etc/ca-certificates')
        yield ReadOnlyBind('/etc/ssl')

    name = 'network'
    pretty_name = 'Network access'
    description = 'Gives access to network.'


class PulseAudio(BubblejailService):
    def __iter__(self) -> ServiceGeneratorType:
        if not self.enabled:
            return

        yield Bind(
            f"{BaseDirectory.get_runtime_dir()}/pulse/native",
            '/run/user/1000/pulse/native'
        )
        yield Symlink('/usr/bin/true', '/usr/local/bin/pulseaudio')

    name = 'pulse_audio'
    pretty_name = 'Pulse Audio'
    description = 'Default audio system in most distros'


class HomeShare(BubblejailService):
    def __init__(self, home_paths: List[str] = EMPTY_LIST):
        super().__init__()
        self.home_paths = OptionStrList(
            str_list=home_paths,
            name='home_paths',
            pretty_name='List of paths',
            description='Add directory name and path to share',
        )
        self.add_option(self.home_paths)

    def __iter__(self) -> ServiceGeneratorType:
        if not self.enabled:
            return

        if self.home_paths is not None:
            for path_relative_to_home in self.home_paths.get_value():
                yield Bind(
                    str(Path.home() / path_relative_to_home),
                    str(Path('/home/user') / path_relative_to_home),
                )

    name = 'home_share'
    pretty_name = 'Home Share'
    description = 'Share directories relative to home'


class DirectRendering(BubblejailService):
    def __init__(self, enable_aco: bool = False):
        super().__init__()
        self.enable_aco = OptionBool(
            boolean=enable_aco,
            name='enable_aco',
            pretty_name='Enable ACO',
            description=(
                'Enables high performance vulkan shader\n'
                'compiler for AMD GPUs. No effect on Nvidia\n'
                'or Intel.'
            ),
        )
        self.add_option(self.enable_aco)

    def __iter__(self) -> ServiceGeneratorType:
        if not self.enabled:
            return

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

        if self.enable_aco.get_value():
            yield EnvrimentalVar('RADV_PERFTEST', 'aco')

    name = 'direct_rendering'
    pretty_name = 'Direct Rendering'
    description = 'Provides access to GPU'


class Systray(BubblejailService):
    def __iter__(self) -> ServiceGeneratorType:
        if not self.enabled:
            return

        yield DbusSessionTalkTo('org.kde.StatusNotifierWatcher')

    name = 'systray'
    pretty_name = 'System tray icons'
    description = (
        'Provides access to Dbus API for creating tray icons\n'
        'This is not the only way to create tray icons but\n'
        'the most common one.'
    )


class Joystick(BubblejailService):
    def __iter__(self) -> ServiceGeneratorType:
        if not self.enabled:
            return

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

    name = 'joystick'
    pretty_name = 'Joysticks and gamepads'
    description = (
        'Windowing systems (x11 and wayland) do not support gamepads.\n'
        'Every game has to read from device files directly.\n'
        'This service provides access to required '
    )


class RootShare(BubblejailService):
    def __init__(self,
                 paths: List[str] = EMPTY_LIST,
                 read_only_paths: List[str] = EMPTY_LIST):
        super().__init__()

        self.paths = OptionStrList(
            str_list=paths,
            name='paths',
            pretty_name='Read/Write paths',
            description='Add directory path to share',
        )

        self.read_only_paths = OptionStrList(
            str_list=read_only_paths,
            name='read_only_paths',
            pretty_name='Read only paths',
            description='Add directory path to share',
        )

        self.add_option(self.read_only_paths)
        self.add_option(self.paths)

    def __iter__(self) -> ServiceGeneratorType:
        if not self.enabled:
            return

        for x in self.paths.get_value():
            yield Bind(x)

        for x in self.read_only_paths.get_value():
            yield ReadOnlyBind(x)

    name = 'root_share'
    pretty_name = 'Root share'
    description = (
        'Share directory relative to root /'
    )


class OpenJDK(BubblejailService):
    def __iter__(self) -> ServiceGeneratorType:
        if not self.enabled:
            return

        yield ReadOnlyBind('/etc/java-openjdk')
        yield ReadOnlyBind('/etc/profile.d/jre.csh')
        yield ReadOnlyBind('/etc/profile.d/jre.sh')

    name = 'openjdk'
    pretty_name = 'Java'
    description = (
        'Enable for applications that require Java\n'
        'Example: Minecraft'
    )


class Notifications(BubblejailService):
    def __iter__(self) -> ServiceGeneratorType:
        if not self.enabled:
            return

        yield DbusSessionTalkTo('org.freedesktop.Notifications')

    name = 'notify'
    pretty_name = 'Notifications'
    description = 'Ability to send notifications to desktop'


SERVICES_CLASSES: Tuple[Type[BubblejailService], ...] = (
    CommonSettings, X11, Wayland,
    Network, PulseAudio, HomeShare, DirectRendering,
    Systray, Joystick, RootShare, OpenJDK, Notifications,
)

ServicesConfDictType = Dict[str, Dict[str, ServiceOptionTypes]]


class ServiceContainer:
    def __init__(self, conf_dict: Optional[ServicesConfDictType] = None):
        self.services = list(
            (service_class() for service_class in SERVICES_CLASSES)
        )
        self.default_service = BubblejailDefaults()

        if conf_dict is not None:
            self.set_services(conf_dict)

    def set_services(
            self,
            new_services_datas: ServicesConfDictType) -> None:

        for service in self.services:
            try:
                new_service_data = new_services_datas.pop(service.name)
            except KeyError as e:
                if e.args != (service.name, ):
                    raise
                else:
                    service.enabled = False
                    continue

            service.set_options(new_service_data)
            service.enabled = True

        if new_services_datas:
            raise TypeError('Unknown conf dict keys', new_services_datas)

    def get_service_conf_dict(self) -> ServicesConfDictType:
        return {service.name: service.to_dict() for service
                in self.services
                if service.enabled}

    def iter_services(self,
                      iter_disabled: bool = False,
                      iter_default: bool = True,
                      ) -> Generator[BubblejailService, None, None]:
        if iter_default:
            yield self.default_service
        for service in self.services:
            if service.enabled or iter_disabled:
                yield service
