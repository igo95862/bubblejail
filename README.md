# Bubblejail

[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/igo95862/bubblejail.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/igo95862/bubblejail/context:python)
[![Total alerts](https://img.shields.io/lgtm/alerts/g/igo95862/bubblejail.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/igo95862/bubblejail/alerts/)
![Python (mypy, flake8)](https://github.com/igo95862/bubblejail/workflows/Python%20(mypy,%20flake8)/badge.svg)

Bubblejail is a [bubblewrap](https://github.com/containers/bubblewrap)-based alternative to Firejail.

## Description

Bubblejail's design is based on observations of Firejail's faults.

One of the biggest issues with Firejail is that you can accidentally run unsandboxed applications and not notice.

Bubblejail, instead of trying to transparently overlay an existing home directory, creates a separate home directory.

Every **Instance** represents a separate home directory. Typically, every sandboxed application has its own home directory.

Each instance has a `services.toml` file which defines the configuration of the instance such as system resources that the sandbox should have access to.

**Service** represents some system resources that the sandbox can be given access to. For example, the Pulse Audio service gives access to the Pulse Audio socket so that the application can use sound.

**Profile** is a predefined set of services that a particular application uses. Using profiles is entirely optional.

## Installation

### Packages

[![Packaging status](https://repology.org/badge/vertical-allrepos/bubblejail.svg)](https://repology.org/project/bubblejail/versions)

[AUR git](https://aur.archlinux.org/packages/bubblejail-git/)

[AUR stable](https://aur.archlinux.org/packages/bubblejail/)

### Manual Installation

If your distro does not have a package you can try to manually install with meson

#### Requirements

* Python 3 (>= 3.9) - python interpreter
* Python XDG - XDG standards for python
* Python Tomli -  TOML file support for python, `tomli` version
* Python Tomli-W - writter part of `tomli`
* Bubblewrap (>= 0.5.0) - sandboxing command line utility
* XDG D-Bus Proxy - filtering dbus proxy
* Desktop File Utils - to manipulate default applications
* Python Qt5 - for GUI
* Meson - build system
* m4 - macro generator used during build
* libseccomp - helper library for seccomp rules
* notify-send - command to send desktop notification (part of `libnotify`)

Optional:

* bash-completion - auto-completions for bash shell
* fish - auto-completions for fish shell

#### Using meson to install

1. Run `meson setup build` to setup build directory
1. Switch to build directory `cd build`
1. Compile `meson compile`
1. Install `sudo meson install`

If you want to uninstall run `ninja uninstall` from build directory.

## Screenshots

Configuration utility

![bubblejailGUI](https://user-images.githubusercontent.com/8576552/107064385-58c50780-67d3-11eb-9399-45e3f565acd3.png)

## Quick start

1. Install bubblejail from [AUR git](https://aur.archlinux.org/packages/bubblejail-git/) or [AUR stable](https://aur.archlinux.org/packages/bubblejail/)
1. Install the application you want to sandbox (for example, firefox)
1. Run GUI. (should be found under name `Bubblejail Configuration`)
1. Press 'Create instance' button at the bottom.
1. Select a profile. (for example, firefox)
1. Optionally change name
1. Press 'Create'
1. The new instance is created along with new desktop entry.

## Command-line utility documentation

See man page:

[man 1 bubblejail](https://github.com/igo95862/bubblejail/blob/master/docs/man/bubblejail.rst)

### Usage examples

#### Create new instance using firefox profile

`bubblejail create --profile firefox FirefoxInstance`

#### Run instance

`bubblejail run FirefoxInstance`

#### Create a generic instance without a desktop entry

`bubblejail create --no-desktop-entry --profile generic Test`

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
* ibus: Multilingual input.

## Available profiles

* firefox
* firefox_wayland: Firefox on wayland
* code_oss: open source build of vscode
* steam
* lutris
* chromium
* transmission-gtk
* generic: most common services, useful for sandboxing applications without profiles

## [TODO](https://github.com/igo95862/bubblejail/blob/master/docs/TODO.md)
