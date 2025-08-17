<!--
SPDX-License-Identifier: GPL-3.0-or-later
SPDX-FileCopyrightText: 2025 igo95862
-->

## AppArmor conflicts with multi-layer sandboxes

Starting from Ubuntu 25.04 a strict AppArmor profile that blocks creating
user namespaces is applied to `bwrap`. While simple programs are not affected,
applications that make use user namespaces such as Chromium or its derivatives
(Brave, etc...) will encounter errors and fail to launch.

See [issue #179](https://github.com/igo95862/bubblejail/issues/179).
