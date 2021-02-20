# SPDX-License-Identifier: GPL-3.0-or-later

# Copyright 2019-2021 igo95862

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

from os import environ, readlink
from pathlib import Path
from random import choices
from string import ascii_letters, hexdigits
from typing import (Any, Dict, FrozenSet, Generator, List, Optional, Set,
                    Tuple, Type, Union, cast, get_args, get_type_hints,
                    Literal)

from xdg import BaseDirectory

from .bwrap_config import (Bind, BwrapConfigBase, DbusCommon, DbusSessionOwn,
                           DbusSessionTalkTo, DevBind, DirCreate,
                           EnvrimentalVar, FileTransfer, LaunchArguments,
                           ReadOnlyBind, SeccompDirective, SeccompSyscallErrno,
                           ShareNetwork, Symlink)
from .exceptions import (ServiceOptionUnknownError,
                         ServiceOptionWrongTypeError, ServiceUnknownError)

# region Service Typing


class ServiceWantsSend:
    ...


class ServiceWantsHomeBind(ServiceWantsSend):
    ...


ServiceIterTypes = Union[BwrapConfigBase, FileTransfer,
                         SeccompDirective,
                         LaunchArguments, ServiceWantsSend, DbusCommon]

ServiceSendType = Union[Path]

ServiceGeneratorType = Generator[ServiceIterTypes, ServiceSendType, None]

ServiceOptionTypes = Union[str, List[str], bool]
SingleServiceOptionsType = Dict[str, ServiceOptionTypes]
MultipleServicesOptionsType = Dict[str, SingleServiceOptionsType]

OptionMeta = Literal['bool', 'str', 'List[str]', 'Union[str, List[str]]']

# endregion Service Typing


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
        lambda s: s.startswith('/usr/')
        or s == '/bin'
        or s == '/sbin',
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


class ServicesDatabase:

    services_classes: Dict[str, Type[ServiceBase]] = {}

    @classmethod
    def get_service(cls, service_name: str) -> Type[ServiceBase]:
        try:
            return cls.services_classes[service_name]
        except KeyError:
            raise ServiceUnknownError(f"Unknown service: {service_name}")

    @classmethod
    def get_service_option_types(
            cls,
            service_name: str,
            option_name: str) -> Tuple[Any, ...]:

        service = cls.get_service(service_name)

        type_hints = get_type_hints(service.iter_args)

        try:
            option_type_hints = type_hints[option_name]
        except KeyError:
            raise ServiceOptionUnknownError(
                f"Unknown option {option_name} of service {service_name}")

        return get_args(option_type_hints)

    @classmethod
    def get_service_options_meta(
            cls,
            service_name: str) -> Dict[str, OptionMeta]:
        service = cls.get_service(service_name)

        type_hints = get_type_hints(service.iter_args)

        option_meta: Dict[str, OptionMeta] = {}

        for option_name, option_type_hints in type_hints.items():
            if option_name == 'return':
                continue

            if option_name == 'kwargs':
                continue

            if option_type_hints == Optional[bool]:
                option_meta[option_name] = 'bool'
            elif option_type_hints == Optional[str]:
                option_meta[option_name] = 'str'
            elif option_type_hints == Optional[List[str]]:
                option_meta[option_name] = 'List[str]'
            elif option_type_hints == Optional[Union[str, List[str]]]:
                option_meta[option_name] = 'Union[str, List[str]]'
            else:
                raise ValueError(
                    f"Unknown option type hints {option_type_hints}")

        return option_meta


class ServiceMeta(type):

    def __new__(cls,
                name: str,
                bases: Tuple[type, ...],
                namespace: Dict[str, Any],
                service_name: str) -> ServiceMeta:

        new_cls = super().__new__(cls, name, bases, namespace)
        assert isinstance(new_cls, ServiceMeta)

        try:
            if issubclass(new_cls, ServiceBase):
                assert service_name not in ServicesDatabase.services_classes, (
                    f'Service name {service_name} in already use'
                )

                ServicesDatabase.services_classes[service_name] = cast(
                    Type[ServiceBase], new_cls)
            else:
                raise ValueError('Class is not a subclass of ServiceBase')
        except NameError:
            ...

        return new_cls


class ServiceBase(metaclass=ServiceMeta, service_name='base'):

    @classmethod
    def iter_args(cls, **kwargs: Any) -> ServiceGeneratorType:
        raise NotImplementedError


class BubblejailDefaults(ServiceBase, service_name='default'):

    @classmethod
    def iter_args(cls, **kwargs: Any) -> ServiceGeneratorType:
        assert not kwargs, (
            f"Unused arguments: {kwargs}"
        )

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
                    yield Symlink(str(readlink(root_path)), str(root_path))
                else:
                    yield ReadOnlyBind(str(root_path))

        # yield ReadOnlyBind('/etc/resolv.conf'),
        yield ReadOnlyBind('/etc/login.defs')  # ???: is this file needed
        # ldconfig: linker cache
        # particularly needed for steam runtime to work
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

        # Set environmental variables
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


class CommonSettings(ServiceBase, service_name='common'):

    @classmethod
    def iter_args(
            cls,
            executable_name: Optional[Union[str, List[str]]] = None,
            share_local_time: Optional[bool] = None,
            filter_disk_sync: Optional[bool] = None,
            dbus_name: Optional[str] = None,
            **kwargs: Any) -> ServiceGeneratorType:
        assert not kwargs, (
            f"Unused arguments: {kwargs}"
        )

        if executable_name is not None:
            # Executable main arguments
            if isinstance(executable_name, str):
                executable_args = [executable_name]
            else:
                executable_args = executable_name

            yield LaunchArguments(executable_args)

        if filter_disk_sync:
            yield SeccompSyscallErrno('sync', 0)
            yield SeccompSyscallErrno('fsync', 0)

        if share_local_time:
            yield ReadOnlyBind('/etc/localtime')

        if dbus_name:
            yield DbusSessionOwn(dbus_name)


class X11(ServiceBase, service_name='x11'):

    @classmethod
    def iter_args(cls, **kwargs: Any) -> ServiceGeneratorType:
        assert not kwargs, (
            f"Unused arguments: {kwargs}"
        )

        for x in XDG_DESKTOP_VARS:
            if x in environ:
                yield EnvrimentalVar(x)

        yield EnvrimentalVar('DISPLAY')
        yield Bind(f"/tmp/.X11-unix/X{environ['DISPLAY'][1:]}")
        yield ReadOnlyBind(environ['XAUTHORITY'], '/tmp/.Xauthority')
        yield ReadOnlyBind('/etc/fonts')
        yield EnvrimentalVar('XAUTHORITY', '/tmp/.Xauthority')
        yield from generate_toolkits()


class Wayland(ServiceBase, service_name='wayland'):

    @classmethod
    def iter_args(cls, **kwargs: Any) -> ServiceGeneratorType:
        assert not kwargs, (
            f"Unused arguments: {kwargs}"
        )

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

        new_socket_path = Path('/run/user/1000') / 'wayland-0'
        yield Bind(str(original_socket_path), str(new_socket_path))
        yield from generate_toolkits()


class Network(ServiceBase, service_name='network'):

    @classmethod
    def iter_args(cls, **kwargs: Any) -> ServiceGeneratorType:
        assert not kwargs, (
            f"Unused arguments: {kwargs}"
        )

        yield ShareNetwork()
        yield ReadOnlyBind('/etc/resolv.conf')
        yield ReadOnlyBind('/etc/ca-certificates')
        yield ReadOnlyBind('/etc/ssl')


class PulseAudio(ServiceBase, service_name='pulse_audio'):

    @classmethod
    def iter_args(cls, **kwargs: Any) -> ServiceGeneratorType:
        assert not kwargs, (
            f"Unused arguments: {kwargs}"
        )

        yield Bind(
            f"{BaseDirectory.get_runtime_dir()}/pulse/native",
            '/run/user/1000/pulse/native'
        )


class HomeShare(ServiceBase, service_name='home_share'):

    @classmethod
    def iter_args(
            cls,
            home_paths: Optional[List[str]] = None,
            **kwargs: Any) -> ServiceGeneratorType:
        assert not kwargs, (
            f"Unused arguments: {kwargs}"
        )

        if home_paths:
            for path_relative_to_home in home_paths:
                yield Bind(
                    str(Path.home() / path_relative_to_home),
                    str(Path('/home/user') / path_relative_to_home),
                )


class DirectRendering(ServiceBase, service_name='direct_rendering'):

    @classmethod
    def iter_args(cls,
                  enable_aco: Optional[bool] = None,
                  **kwargs: Any) -> ServiceGeneratorType:
        assert not kwargs, (
            f"Unused arguments: {kwargs}"
        )

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

        if enable_aco:
            yield EnvrimentalVar('RADV_PERFTEST', 'aco')


class Systray(ServiceBase, service_name='systray'):

    @classmethod
    def iter_args(cls, **kwargs: Any) -> ServiceGeneratorType:
        assert not kwargs, (
            f"Unused arguments: {kwargs}"
        )

        yield DbusSessionTalkTo('org.kde.StatusNotifierWatcher')


class Joystick(ServiceBase, service_name='joystick'):

    @classmethod
    def iter_args(cls, **kwargs: Any) -> ServiceGeneratorType:
        assert not kwargs, (
            f"Unused arguments: {kwargs}"
        )

        look_for_names: Set[str] = set()

        dev_input_path = Path('/dev/input')
        sys_class_input_path = Path('/sys/class/input')
        js_names: Set[str] = set()
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
            yield DevBind(str(dev_input_path / dev_name))

            sys_class_path = sys_class_input_path / dev_name

            yield Symlink(
                str(readlink(sys_class_path)),
                str(sys_class_path)
            )

            pci_path = sys_class_path.resolve()
            yield DevBind(str(pci_path.parents[2]))


class RootShare(ServiceBase, service_name='root_share'):

    @classmethod
    def iter_args(cls,
                  paths: Optional[List[str]] = None,
                  read_only_paths: Optional[List[str]] = None,
                  **kwargs: Any) -> ServiceGeneratorType:
        assert not kwargs, (
            f"Unused arguments: {kwargs}"
        )

        if paths:
            for x in paths:
                yield Bind(x)

        if read_only_paths:
            for x in read_only_paths:
                yield ReadOnlyBind(x)


class OpenJDK(ServiceBase, service_name='openjdk'):

    @classmethod
    def iter_args(cls, **kwargs: Any) -> ServiceGeneratorType:
        assert not kwargs, (
            f"Unused arguments: {kwargs}"
        )

        yield ReadOnlyBind('/etc/java-openjdk')
        yield ReadOnlyBind('/etc/profile.d/jre.csh')
        yield ReadOnlyBind('/etc/profile.d/jre.sh')


class Notifications(ServiceBase, service_name='notify'):

    @classmethod
    def iter_args(cls, **kwargs: Any) -> ServiceGeneratorType:
        assert not kwargs, (
            f"Unused arguments: {kwargs}"
        )

        yield DbusSessionTalkTo('org.freedesktop.Notifications')


class GnomeToolkit(ServiceBase, service_name='gnome_toolkit'):

    @classmethod
    def iter_args(
            cls,
            gnome_portal: Optional[bool] = None,
            dconf_dbus: Optional[bool] = None,
            gnome_vfs_dbus: Optional[bool] = None,
            **kwargs: Any) -> ServiceGeneratorType:
        assert not kwargs, (
            f"Unused arguments: {kwargs}"
        )

        if gnome_portal:
            yield EnvrimentalVar('GTK_USE_PORTAL', '1')
            yield DbusSessionTalkTo('org.freedesktop.portal.*')

        if dconf_dbus:
            yield DbusSessionTalkTo('ca.desrt.dconf')

        if gnome_vfs_dbus:
            yield DbusSessionTalkTo('org.gtk.vfs.*')

        # TODO: org.a11y.Bus accessibility services
        # Needs both dbus and socket, socket is address is
        # acquired from dbus


class ServicesConfig:
    def __init__(
            self,
            services_config_dict: MultipleServicesOptionsType) -> None:

        if unknown_services := (
            services_config_dict.keys()
            - ServicesDatabase.services_classes.keys()
        ):
            raise ServiceUnknownError(f"Unknown services: {unknown_services}")

        for service_name, service_options in services_config_dict.items():
            for option_name, option_value in service_options.items():
                self.validate_value_for_option(
                    service_name, option_name, option_value)

        self.services_dicts = services_config_dict

    def validate_value_for_option(
            self, service_name: str,
            option_name: str,
            option_value: ServiceOptionTypes) -> None:
        possible_types = ServicesDatabase.get_service_option_types(
            service_name, option_name)

        for type_to_check in possible_types:

            if type_to_check is List[str]:

                if not isinstance(option_value, list):
                    continue

                if (all((isinstance(x, str) for x in option_value))):
                    return

            if isinstance(option_value, type_to_check):
                return

        raise ServiceOptionWrongTypeError(
            f"Option {option_name} of service "
            f"{service_name} has wrong type "
            f"{type(option_value)}"
        )

    def enable_service(self, service_name: str) -> None:
        try:
            ServicesDatabase.services_classes[service_name]
        except KeyError:
            raise ServiceUnknownError(
                f"Tried to add unknown service: {service_name}")

        self.services_dicts[service_name] = {}

    def disable_service(self, service_name: str) -> None:
        try:
            self.services_dicts.pop(service_name)
        except KeyError:
            raise ServiceUnknownError(
                "Tried to remove unknown or "
                f"not enabled service: {service_name}"
            )

    def set_service_option(self,
                           service_name: str,
                           option_name: str,
                           option_value: ServiceOptionTypes) -> None:
        self.validate_value_for_option(
            service_name,
            option_name,
            option_value)

        self.services_dicts[service_name][option_name] = option_value

    def get_service_option(self,
                           service_name: str,
                           option_name: str) -> ServiceOptionTypes:
        try:
            service_dict = self.services_dicts[service_name]
        except KeyError:
            raise ServiceUnknownError(
                f"Service unknown or not enabled: {service_name}"
            )

        try:
            option_value = service_dict[option_name]
        except KeyError:
            raise ServiceOptionUnknownError(
                f"Service {service_name} option {option_value} "
                "unknown or not enabled"
            )

        return option_value

    def iter_services(self) -> ServiceGeneratorType:
        yield from BubblejailDefaults.iter_args()
        for service_name, service_conf in self.services_dicts.items():
            yield from ServicesDatabase.services_classes[
                service_name].iter_args(**service_conf)
