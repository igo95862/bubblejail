<!--
SPDX-License-Identifier: GPL-3.0-or-later
SPDX-FileCopyrightText: 2023 igo95862
-->
## Missing recommended packages

Alpine Linux packaging does not support optional
dependencies. Some highly recommended packages are
missing from bubblejail dependencies.

List of recommended packages to install:

* `desktop-file-utils` - updates desktop entry cache and lets
  bubblejail instances be selected as default applications.
* `libnotify` - when bubblejail fails to start sends a
  notification to desktop rather than failing silently.
