# Bubblejail


Bubblejail is a [bubblewrap](https://github.com/containers/bubblewrap) based alternative to firejail.


It is in very early development phase so expect bugs and lack of features.


# How to use

1. Install bubblejail from [AUR](https://aur.archlinux.org/packages/bubblejail-git/)
1. Install the application you want to sandbox. (for example, firefox)
1. Create an instance using the application profile

> bubblejail create --profile=firefox myfirefox

1. The desktop entry should be created and can be found under name _myfirefox bubble_


# Avalible profiles

* Firefox
* Firefox on wayland

# Known issues

* No way to spawn new commands inside already launched sandbox. This will cause issues with such things as opening links in a browser from another application. Possible solution is to use --userns option of bubblewrap.
