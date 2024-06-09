# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2019-2022 igo95862
from __future__ import annotations


class BubblejailException(Exception): ...


class ServiceError(BubblejailException): ...


class ServiceConflictError(ServiceError): ...


class BubblejailInstanceNotFoundError(BubblejailException): ...


class BubblewrapRunError(BubblejailException): ...


class BubblejailLibseccompError(BubblejailException): ...


class LibseccompSyscallResolutionError(BubblejailLibseccompError): ...


class BubblejailInitializationError(BubblejailException): ...


class BubblejailDependencyError(BubblejailInitializationError): ...
