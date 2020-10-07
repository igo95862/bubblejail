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
1. Run GUI.
1. Press 'Create instance' button at the bottom.
1. Select a profile. (for example, firefox)
1. Optionally change name
1. Press 'Create'
1. The new instance is created along with new desktop entry.

## Command-line utility documentation

Command line program `bubblejail` has 5 subcommands: `create`, `run`, `list`, `edit`, and `auto-create`.

### bubblejail create

Creates a new instance.

Optional arguments:

* __--profile__ Specify the profile that the instance will use. For available profiles, look at the **Available profiles** section. If omitted an empty profile will be used and the user will have to define the configuration manually.
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

Running with default arguments:
```
bubblejail run myfirefox
```

Passing arguments:
```
bubblejail run myfirefox firefox google.com
```

### bubblejail list

Lists profiles or instances.

Required arguments:

* type List either `instances`, `profiles` or `services`

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

## Editing services.toml

Instance configuration is written in the [TOML](https://github.com/toml-lang/toml) format.

**services.toml** file is located at `$XDG_DATA_HOME/bubblejail/instances/{name}/services.toml`.

The `edit` command can be used to open the config file in your EDITOR and validate after editing.

Example config:

```
[common]
executable_name = ["/usr/bin/firefox",] # This setting is optional.

[wayland]
[network]
[pulse_audio]
[direct_rendering]

[home_share]
home_paths = [ "Downloads",]
```

### Available services

* common: settings that are not categorized
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
