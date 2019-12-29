from .bwrap_config import (BwrapArgs, Bind, ReadOnlyBind,
                           EnvrimentalVar)

X11 = BwrapArgs(
    binds=[Bind('/tmp/.X11-unix/X0')],
    env_no_unset={'DISPLAY', },
    read_only_binds=[ReadOnlyBind('/etc/fonts/fonts.conf')],
)

Wayland = BwrapArgs(
    binds=[Bind('/run/user/1000/wayland-0'),
           Bind('/run/user/1000/wayland-0.lock')],
    env_no_unset={'WAYLAND_DISPLAY', 'XDG_RUNTIME_DIR'},
    enviromental_variables=[EnvrimentalVar('GDK_BACKEND', 'wayland')])

Network = BwrapArgs()
Network.share_network = True

PulseAudio = BwrapArgs(
    binds=[
        Bind('/run/user/1000/pulse/native'),
    ]
)

__all__ = ["X11", "Network"]
