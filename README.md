# Bubblejail

[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/igo95862/bubblejail.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/igo95862/bubblejail/context:python)
[![Total alerts](https://img.shields.io/lgtm/alerts/g/igo95862/bubblejail.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/igo95862/bubblejail/alerts/)

Bubblejail is a [bubblewrap](https://github.com/containers/bubblewrap) based alternative to firejail.


It is in very early development phase so expect bugs and lack of features.


## How to use

1. Install bubblejail from [AUR](https://aur.archlinux.org/packages/bubblejail-git/)
1. Install the application you want to sandbox. (for example, firefox)
1. Create an instance using the application profile

> bubblejail create --profile=firefox myfirefox

1. The desktop entry should be created and can be found under name _myfirefox bubble_

## Command line utility documentation

Command line program `bubblejail` has 3 sub commands: `create`, `run`, `list`

### bubblejail create

Creates a new instance.

Required arguments: 

* --profile Specify the profile that the instance will use. For avalible profiles look at **Avalible profiles** section
* instance name that the new instance will use 

Example:

```
bubblejail create --profile=firefox FirefoxSandbox
```

### bubblejail run

Runs the specified instance. Optionally pass arguments to instance.

Required arguments: 

* instance name

Optional arguments: 

* arguments to instance

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


## Avalible profiles

### Firefox

Firefox running on X11 protocol.

Profile name: firefox

### Firefox on wayland

Firefox running on wayland without Xwayland access. Tested on GNOME not sure if it works on other wayland compositors.

Profile name: firefox_wayland

## Known issues

* No way to spawn new commands inside already launched sandbox. This will cause issues with such things as opening links in a browser from another application. Possible solution is to use --userns option of bubblewrap.
