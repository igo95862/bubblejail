# Bubblejail

[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/igo95862/bubblejail.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/igo95862/bubblejail/context:python)
[![Total alerts](https://img.shields.io/lgtm/alerts/g/igo95862/bubblejail.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/igo95862/bubblejail/alerts/)

Bubblejail is a [bubblewrap](https://github.com/containers/bubblewrap)-based alternative to Firejail.

## Description

Bubblejail's design is based on observations of Firejail's faults.

One of the biggest issues with Firejail is that you can accidentally run unsandboxed applications and not notice.

Bubblejail, instead of trying to transparently overlay an existing home directory, creates a separate home directory.

Every **Instance** represents a separate home directory. Typically, every sandboxed application has its own home directory.

Each instance has a `config.toml` file which defines the configuration of the instance such as system resources that the sandbox should have access to.

**Service** represents some system resources that the sandbox can be given access to. For example, the Pulse Audio service gives access to the Pulse Audio socket so that the application can use sound.

**Profile** is a predefined set of services that a particular application uses. Using profiles is entirely optional.

## Quick start

1. Install bubblejail from [AUR](https://aur.archlinux.org/packages/bubblejail-git/)
1. Install the application you want to sandbox (for example, firefox)
1. Run `auto-create` command that will look for possible applications to sandbox.
1. The desktop entry should be created and can be found under name __{Name} bubble__

## Command-line utility documentation

Command line program `bubblejail` has 5 subcommands: `create`, `run`, `list`, `edit`, and `auto-create`.

### bubblejail create

Creates a new instance.

Optional arguments:

* __--profile__ Specify the profile that the instance will use. For available profiles, look at the **Available profiles** section. If omitted an empty profile will be used and the user will have to define the configuration manually.
* __--do-import__ Imports data from a home directory. **DOES NOT WORK YET**
* __--no-desktop-entry__ Do not create a desktop entry.

Required arguments:

* name that the new instance will use

Example:

```
bubblejail create --profile=firefox FirefoxSandbox
```

### bubblejail run

Runs the specified instance, optionally passing arguments to the instance.

Required arguments:

* instance name

Optional arguments:

* instance arguments
* __--debug-shell__ Opens a shell inside the sandbox instead of running the command.
* __--dry-run__ Prints the bwrap arguments and exits.
* __--debug-log-dbus__ Enables dbus proxy log.

Example:

```
bubblejail run myfirefox google.com
```

### bubblejail list

Lists profiles or instances.

Required arguments:

* type List either instances or profiles

Example:

```
bubblejail list instances
```

### bubblejail edit

Opens the configuration file in the EDITOR. After exiting the editor, the file is validated and only written if validation is successful.

Example:

```
bubblejail edit myfirefox
```

### bubblejail auto-create

Tries to create new instances based on available profiles.

## Editing config.toml

Instance configuration is written in the [TOML](https://github.com/toml-lang/toml) format.

**config.toml** file is located at `$XDG_DATA_HOME/bubblejail/instances/{name}/config.toml`.

The `edit` command can be used to open the config file in your EDITOR and validate after editing.

Example config:

```
executable_name = ["/usr/bin/firefox", "--class=bubble_Firefox", "--name=bubble_Firefox"]
services = [
  "x11", "network", "pulse_audio",
]

[service.home_share]
home_paths = [ "Downloads",]
```

### Config keys

* executable_name: Either a single string or a list that contains that executable name and arguments. Required unless you use the --debug-shell option to open shell.
* share_local_time: boolean that controls if the local time is shared with the sandbox. On by default.
* filter_disk_sync: boolean that makes application unable to force disk flush.
* services: List of strings. Adds services without parameters.
* service.{name}: Used to configure a particular service. The service does not need to be added to the services list as it will be enabled if a particular configuration section exists.

### Available services

* x11: X windowing system. Also includes Xwayland.
* wayland: Pure wayland windowing system.
* network: Access to network.
* pulse_audio: Pulse Audio audio system.
* home_share: Shared folder relative to home.
    * home_paths: List of path strings to share with sandbox. Required.
* direct_rendering: Access to GPU.
    * enable_aco: Boolean to enable high performance Vulkan compiler for AMD GPUs.
* systray: Access to the desktop tray bar.
* joystick: Access to joysticks and gamepads.
* root_share: Share access relative to /.
    * paths: List of path strings to share with sandbox. Required.
* openjdk: Access to Java libraries.
* notify: Access to desktop notifications.

## Available profiles

### Firefox

Firefox running on X11 protocol.

Profile name: firefox

### Firefox on wayland

Firefox running on wayland without Xwayland access. Tested on GNOME not sure if it works on other wayland compositors.

Profile name: firefox_wayland

### Code OSS

Open source build of VScode.

Profile name: code_oss

### Steam

Steam with runtime.

Profile name: steam

### Lutris

Lutris open-source gaming platform.

Profile name: lutris

## TODO

* Graphical toolkits settings are not passed.
