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
* **Home directory is now in same position from the prespective of sandbox**
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
