## From 0.2

### New configuration location and format

In version 0.3 the location of the instance configuration file
has changed as well as the in file format.

Old under `instance_name/config.toml`:
```
executable_name = "/usr/bin/firefox"
services = [
  "wayland", "network", "pulse_audio", "direct_rendering",
]

[service.home_share]
home_paths = [ "Downloads",]
```

New under `instance_name/services.toml`:
```
[common]
executable_name = "/usr/bin/firefox"

[wayland]
[network]
[pulse_audio]
[direct_rendering]

[home_share]
home_paths = [ "Downloads",]
```

There is an automatic conversion script that should run with next
invocation of bubblejail, however, it will not preserve the comments.

If you want to manually convert your configuration file:

1. Copy `config.toml` to `services.toml`
1. Move all uncategorized keys (i.e. `executable_name`) under `common` section.
1. Put all values inside services array as a names of new sections. (`services = ['x11', 'network']` to `[x11]` and `[network]`)
1. Remove `service.` from section names. (`[service.home_share]` to `[home_share]`)

### Run command behavior change and `executable_name` key

Run command now does not prepend the `executable_name` unless during initialization no arguments were passed.
Desktop entries overwrites now preserve all arguments.
It is recommended to regenerate all desktop entries.

### Imports have been removed

Due to complexity. There are now import tips that might help you import your application in to instance.

### Dbus is now always proxied. GTK applications might require dbus name ownership.

GTK applications seem to crash if the dbus is present but they are unable to acquire the name.
For example, `tranmsission-gtk` requires `com.transmissionbt.*` dbus ownership.
This setting is controlled by  'Dbus name' (`dbus_name`) setting under common settings.