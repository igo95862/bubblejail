# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2023 igo95862
from __future__ import annotations


class NamespacesConstants:
    # x86_64 constants
    SYSCALL_SETNS: int = 308
    NS_GET_USERNS: int = 46849
    NS_GET_PARENT: int = 46850
