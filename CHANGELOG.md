<!--
SPDX-License-Identifier: GPL-3.0-or-later
SPDX-FileCopyrightText: 2023 igo95862
-->

# 0.9.2

## Features

* Access to CPU topology under `/sys/devices/system/cpu` is now provided by default.
  A lot of modern applications makes use of it. (Chromium, WINE...)
  Steam profile already used root share service to pass `/sys/devices/system/cpu`.
  This change should compatible with existing Steam instances.

## Fixes

* Fixed Nvidia graphics not working with `direct_rendering` service.
  The recent 500+ driver requires access to the `/sys/module/nvidia/initstate` file.
  (reported by @consolation548 and tested by @gnusenpai)

# 0.9.1

## Features

* New icon designed by @gelatinbomb

## Fixes

* Fix WebKit built-in sandboxing not working.
* Fix missing comma in default syscall filter preventing certain filters from working.
  (contributed by @rusty-snake)

# 0.9.0

No changes since 0.9rc1.

# 0.9rc1

## Major build changes!

* **New dependency!** [python-lxns](https://github.com/igo95862/python-lxns) is
  a Python library to control Linux kernel namespaces. For convenience the library
  is available as a meson subproject and is bundled in source archive. Set `use-vendored-python-lxns`
  build option to true to enable meson subproject. If you are a distro maintainer
  it is recommended to package python-lxns independently and mark it as dependency.
* `allow-site-packages-dir` was removed. Unfortunately it is impossible to control Python
  packages install dir with meson. If you still want to install bubblejail in to site-pacakges
  you can either patch `meson.build` or use `meson rewrite kwargs delete project / default_options ""`
  command in source prepare step.
* `bytecode-optimization` build option is replaced with meson's
  native `python.bytecompile`. Most distros meson wrappers already set this
  option.
* `tomli` support has been dropped. `tomlib` from Python 3.11
  standard library is the only supported TOML reading library.
  (note that `tomli-w` is still a requirement)

## Features

* Source code licensing is now verified with [REUSE](https://reuse.software/).
* Log messages now always use stderr.

## Fixes

* Fix bubblejail-config GUI utility not using its icon. (reported by @boredsquirrel and @rusty-snake)
* Fix Chromium and Firefox profiles not working on certain distros because of
  diverging desktop entry names. (reported by @boredsquirrel)
* Fix instance being left in inoperable state if D-Bus proxy failed to initialize.
* Fix `namespaces_limits` service sometimes failing because of concurrency races
  with sandboxed PID.
* Fixed several typos and added codespell to the CI.

# 0.8.3

## Features

* Add `debug` service which can be used to add arguments to `bwrap`
  and `xdg-dbus-proxy` invocations. See `bubblejail.services` man page
  for its configuration keys and values. (requested by @xiota)
* Document directories used by bubblejail in `bubblejail` man page.
  (requested by @firefoxlover)

## Fixes

* Mount file pointed by symlink if `/etc/resolv.conf` is a symlink when `network`
  service is used. This fixes DNS issues when systemd-resolved is used.
  (first reported by @adworacz)
* Fixed `joystick` description not being complete. (reported by @xiota)
* Fixed `PYTHONPYCACHEPREFIX` environment variable breaking build system.
  (first reported by `mlj` on AUR)

# 0.8.2

## Fixes

* Fix slirp4netns service sometimes failing because of wrong user namespace
  being passed. (reported by @xiota)
* Fix bubblejail sometimes continuing to run even if some service failed to
  initialize. (reported by @xiota)

# 0.8.1

## Features

* Added support for `tomllib` standard library package for reading TOML files.
  It is available since Python 3.11. `tomli` package is now only needed if
  running on Python 3.10. (note that TOML writing library `tomli-w` is still
  required)
* Using `run` command on an already running instance now prints a message to stderr
  that the instance already running and the commands that will be sent to instance.
* Tightened D-Bus filtering rules for Notifications and Systray services. Turns out
  a lot of D-Bus servers for those services expose too many interfaces than required.
  (thank you @rusty-snake for pointing this out)

## Fixes

* Fixed trying to create config directories on access. If a system wide directory was
  missing like `/etc/bubblejail/profiles/` bubblejail would fail to run.
  (reported by @rusty-snake)
* Removed isolated python mode for build scripts. This makes it easier to build bubblejail
  when meson or Python is installed in non system directory. (fixed with the help of @eli-schwartz)
* Fixed `slirp4netns` initialization failure being ignored. Now if `slirp4netns` fails to
  start bubblejail will also fail. (reported by @xiota)
* Fixed running bubblejail without arguments raising exception instead of help text.
  (fixed by @rusty-snake)
* Fixed `namespaces_limits` initialization failure being ignored. Now if `namespaces_limits`
  fails to set namespace limits bubblejail will also fail. (reported by @rusty-snake)

# 0.8.0

## Fixes

* Fixed X11 multi-screen not working. (the single screen spanning multiple displays already works)
* Fixed default arguments not being used when no arguments have been passed to run command.

# 0.8.RC2

## Fixes

* Fixed GUI not working because of integer settings that `namespaces_limits`
  uses.

# 0.8.RC1

## Added `namespaces_limits` service

Linux namespaces are a powerful instruments that can be used to create
sandboxes but it also exposes internal kernel interfaces to unprivileged users
which can be a source of vulnerabilities. (for example CVE-2022-25636)

New service `namespaces_limits` will limit amount of namespaces that
could be created inside sandbox.

It has `user`, `mount`, `pid`, `ipc`, `net`, `time`, `uts` and `cgroup`
settings which corresponds to each type of namespace. Those settings take
an integer as value with `0` (default) completely disabling creating that
type of namespace, `-1` allowing unlimited amount and any positive integer
sets limit to that number. The positive integer is useful in case your application
will only create a limited number of namespaces.

Profiles might receive a well tested namespaces limits in the future version.

## Dependencies changes

* GUI has been ported to PyQt6.

## Build changes

* Fixed `libseccomp` and `python-xdg` being required during build.
* Added meson option to disable man page build and installation.
* Added meson install tags. Current tags are `runtime` for core files and cli tool,
  `bubblejail-gui` for gui configuration tool, `fish-completion`/`bash-completion`
  for shell autocompletion and `man` for man pages.
  (thank you @gordon-quad)

## Known issues

* `slirp4netns` and `namespaces_limits` can conflict with each other because
  `slirp4netns` tries to switch to new mount namespace.
* Namespaces functions only work on x86_64 platform.

# 0.7.0

* **m4 macro processor removed as build dependency**
* **jinja2 template engine is now a build requirement**
* **Sphinx removed as build dependency**
* **scdoc is now used to build man pages.** This is optional build dependency.
  If scdoc is not present the man pages will not be built.
* Added `bubblejail.services` man page that contains information about all
  services and their options.
* **Added build option to specify bytecode optimization level.**
  Optimization level should match your distro optimization level or there
  will be start-up penalty. Option is named `bytecode-optimization` and takes
  an integer from 0 to 2.
* Added `slirp4netns` service. It is a custom networking stack for the sandbox.
  Allows to disconnect sandbox from loopback interface or bind it to a specific
  device or address. Currently only available on x86_64 platforms.
  Requires `slirp4netns` binary be installed.
* Added service conflicts. Conflicting services can't be activated together.
  Currently `ibus` conflicts `fcitx` and `network` conflicts with `slirp4netns`.
* Profiles can now be defined in `/etc/bubblejail/profiles` folder and will be
  available to any user on the system.

# 0.6.2

## Fixes
* Fixed generated empty desktop entries not having `Type=` key.
* Fixed XAUTHORITY not being optional.
* Fixed desktop notification about bubblewrap exiting with error
  being sent every time sandbox closes.

# 0.6.1

* Fixed an edge case when users home directory overlapped with legacy location
* `notify-send` is now more optional. No longer raises extra exception
  if it is missing.
* Desktop notification is now sent on any bubblewrap non-zero exit code

# 0.6.0

* **`/etc` is now shared with sandbox. This is potentially breaking change**
* **Home directory is now in same position from the perspective of sandbox**
* **Removed support for old `toml` python package**
* Desktop notification is now sent if sandbox fails to start. (new dependency on `notify-send`)
* Added Fcitx service (thanks @h0cheung)
* Deprecated `share_local_time` option of common settings
* Deprecated `enable_aco` option of DRI

# 0.5.3

* Added `--version` command line option. Distro packagers can modify it with `version_display` meson option. (would be helpful for bug reports to show distro and version)
* Fixed Nvidia Optimus not working with Direct Rendering service. Thanks @gnusenpai for debugging this issue.

# 0.5.2

* Added IBus service. (multilingual input) Thanks @h0cheung

# 0.5.1

* **Fixed any instance creation failing**

# 0.5.0

* **Minimum bubblewrap version is now 0.5.0**
* **Added default seccomp filter with several syscalls that might be dangerous**
* **Switched TOML package from toml to tomli and tomli-w**
* Added build option to use pythons site-package directory instead of version independent one
* Fixed running on arch other than x86_64
* Fixed trying to bind glibc linker cache on non glibc system

# 0.4.4

* Fixed D-Bus proxy initialization having a race condition that could have caused startup failures
* Fixed Video4Linux services failing to start if there are no video devices

# 0.4.3

* Added Video4Linux service
* Added Pipewire service
* New gamepad resolution algorithm (bluetooth support)
* Fixed module loading having side effects of creating config directory

# 0.4.2

* Build system updates. Now supports custom prefixes
* Man page for `bubblejail`
* `edit` command now only overwrites if you modified the config
* Added `--debug-bwrap-args` that adds extra args to bwrap
* Dropped Pulse Audio work-around as Arch Linux fixed issue with Steam package
