# General

* Some kind of dependency system for services? For example, both wayland and x11 want toolkits settings so they both can depend on toolkit settings service.
* Passing file outside of sandbox to be opened by another application or sandbox. For example, being able to download a torrent from browser sandbox and pass it to torrent client sandbox. Flatpak has something like this with a dialoge.
* MIME. Creating sanbox desktop entry overwrite detroyes MIME associations. (found update-desktop-database desktop-file-utils)
* Free up temp files after the communication with helper has been established.

# Applications

More profiles for commonly used applications.
Maybe check Arch Linux stats for commonly used applications?

## Firefox

Figure out why Firefox gives "already running but not responding"
It seems like it uses some weird X11 IPC to communicate.
When I was running KDE it would create the new sandbox windows even when launching un-sandboxed desktop entry. 
Obviously does not work on Wayland. (upstream bug?)

# Services

## GTK

* How does directory metadata is shared. If you sort a directory by size, it is somehow is remmebered when not sandboxed. Is it a Dbus API? a file?
* Is sharing recent file metadata folder safe? (under `~/.local/share/recently-used.xbel`)
* Accessibilty bus.
..* Talk to `org.a11y.Bus` dbus.
..* There is also a GetAddress() method? Is it needed?
* Bookmarks. (`~/.config/gtk-3.0/bookmarks`)

## Wayland

* Being able to spawn an independent Xwayland server. (possibly fixes Firefox)

## Direct Rendering

* Being able to select which DRI device to pass. (not sure how I can test without having access to PC with two graphics cards)

## Network

* Custom resolv.conf per instance? Can this be a solution for captive portals in cases when you use dnscrypt-proxy.
* Custom gai.conf? Being able to prefer ipv4 or ipv6 per instance. Can you even prefer a specific route? (for VPNs)

# GUI

* Error message screens
* Options window becoming too large as more and more options are being added
* Same with profiles drop down

# Docs

* Replace long README with man pages and online docs?

# New ideas

* Being able to run ephemeral home directory that gets destroyed after closing.
* Preload certain files in to memory to speed up startup? (looking at you Steam) vmtouch exists but is not packaged in Arch.
