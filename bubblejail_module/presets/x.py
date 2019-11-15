from ..bwrap_config import (BwrapArgs, Bind, ReadOnlyBind)

X_PRESET = BwrapArgs(
    binds=[Bind('/tmp/.X11-unix/X0')],
    env_no_unset={'DISPLAY', },
    read_only_binds=[ReadOnlyBind('/etc/fonts/fonts.conf')],
)

__all__ = ["X_PRESET"]
