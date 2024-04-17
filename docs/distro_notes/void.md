## Void Linux missing `/etc/machine-id` file

### Affected applications

**Steam**: Steam will show empty black window instead of store or library pages.

### Solution

Void Linux is missing `/etc/machine-id` file (which contains D-Bus UUID).
However, it still has the `/var/lib/dbus/machine-id` file. This location
can be passed to sandbox with `root_share` service.

See [issue #40](https://github.com/igo95862/bubblejail/issues/40).
