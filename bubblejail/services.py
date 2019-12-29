from xdg import BaseDirectory
from os import environ
from .bwrap_config import (BwrapArgs, Bind, ReadOnlyBind,
                           EnvrimentalVar)

X11 = BwrapArgs(
    binds=[Bind(f"/tmp/.X11-unix/X{environ['DISPLAY'][1:]}")],
    env_no_unset={'DISPLAY', },
    read_only_binds=[ReadOnlyBind('/etc/fonts/fonts.conf')],
)

Wayland = BwrapArgs(
    binds=[Bind((f"{BaseDirectory.get_runtime_dir()}"
                 f"/{environ['WAYLAND_DISPLAY']}")), ],
    env_no_unset={'WAYLAND_DISPLAY', 'XDG_RUNTIME_DIR'},
    enviromental_variables=[EnvrimentalVar('GDK_BACKEND', 'wayland')])

Network = BwrapArgs()
Network.share_network = True

PulseAudio = BwrapArgs(
    binds=[
        Bind(f"{BaseDirectory.get_runtime_dir()}/pulse/native"),
    ]
)

__all__ = ["X11", "Network"]
