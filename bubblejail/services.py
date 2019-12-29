from .bwrap_config import (BwrapArgs, Bind, ReadOnlyBind)

X11 = BwrapArgs(
    binds=[Bind('/tmp/.X11-unix/X0')],
    env_no_unset={'DISPLAY', },
    read_only_binds=[ReadOnlyBind('/etc/fonts/fonts.conf')],
)

Network = BwrapArgs()
Network.share_network = True

__all__ = ["X11", "Network"]
