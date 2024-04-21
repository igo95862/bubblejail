<!--
SPDX-License-Identifier: GPL-3.0-or-later
SPDX-FileCopyrightText: 2020 igo95862
-->
# General

* Need Dbus support for stuff like systemd integration. Waiting on my new dbus library. https://github.com/igo95862/py-sd-bus
* Maybe port GUIs to Dbus integration. Less spagthetti, GTK and Qt will be written in native languages. (C and C++)
* Some kind of dependency system for services? For example, both wayland and x11 want toolkits settings so they both can depend on toolkit settings service.
* Passing file outside of sandbox to be opened by another application or sandbox. For example, being able to download a torrent from browser sandbox and pass it to torrent client sandbox. Use xdg-desktop-portal for this.
* Free up temp files after the communication with helper has been established.

# Applications

More profiles for commonly used applications.
Maybe check Arch Linux stats for commonly used applications?

# Services

* Use `sd-device` to search for device attributes. `libudev` is actually deprecated. `sd-device` can be added to my D-Bus library.

## GTK

* How does directory metadata is shared. If you sort a directory by size, it is somehow is remembered when not sandboxed. Is it a Dbus API? a file?
* Is sharing recent file metadata folder safe? (under `~/.local/share/recently-used.xbel`)
* Accessibility bus.
..* Talk to `org.a11y.Bus` dbus.
..* There is also a GetAddress() method? Is it needed?
* Bookmarks. (`~/.config/gtk-3.0/bookmarks`)

## Wayland

* Being able to spawn an independent Xwayland server. Needs compositor support. How do I ask GNOME team to consider such option?

## Direct Rendering

* Being able to select which DRI device to pass. (not sure how I can test without having access to PC with two graphics cards)

# GUI

* Error message screens
* Options window becoming too large as more and more options are being added
* Same with profiles drop down

# New ideas

* Being able to run ephemeral home directory that gets destroyed after closing.
* Preload certain files in to memory to speed up startup? (looking at you Steam) vmtouch exists but is not packaged in Arch.
* New command ``terminal``. Spawns a terminal inside the instance.

