# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 igo95862
from __future__ import annotations

from unittest import TestCase

from bubblejail.dbus_proxy import DBusProxyLogParser

NAME_ACQUIRED_FAILED = """C2: -> org.freedesktop.DBus call org.freedesktop.DBus.RequestName at /org/freedesktop/DBus
Filtering message due to arg0 org.gnome.clocks, policy: 0 (required 3)"""

GET_OWNER_NAME_FAILED = """C6: -> org.freedesktop.DBus call org.freedesktop.DBus.GetNameOwner at /org/freedesktop/DBus
Filtering message due to arg0 org.freedesktop.Notifications, policy: 0 (required 1)
"""

START_SERVICE_BY_NAME_FAILED = """C5: -> org.freedesktop.DBus call org.freedesktop.DBus.StartServiceByName at /org/freedesktop/DBus
Filtering message due to arg0 org.freedesktop.Notifications, policy: 0 (required 2)"""

HIDDEN_CALL = """C7: -> org.freedesktop.Notifications call org.freedesktop.Notifications.GetServerInformation at /org/freedesktop/Notifications
*HIDDEN* (ping)"""

NO_ERRORS = """C1: -> org.freedesktop.DBus call org.freedesktop.DBus.Hello at /org/freedesktop/DBus
C-65536: -> org.freedesktop.DBus fake AddMatch for org.freedesktop.Notifications
C-65535: -> org.freedesktop.DBus fake GetNameOwner for org.freedesktop.Notifications
B-1: <- org.freedesktop.DBus return from C1
B-1: <- org.freedesktop.DBus signal org.freedesktop.DBus.NameAcquired at /org/freedesktop/DBus
B-1: <- org.freedesktop.DBus return from C-65536
*SKIPPED*
B-1: <- org.freedesktop.DBus return from C-65535
*SKIPPED*
C2: -> org.freedesktop.DBus call org.freedesktop.DBus.AddMatch at /org/freedesktop/DBus
C3: -> org.freedesktop.DBus call org.freedesktop.DBus.GetNameOwner at /org/freedesktop/DBus
C4: -> org.freedesktop.DBus call org.freedesktop.DBus.AddMatch at /org/freedesktop/DBus
C5: -> org.freedesktop.DBus call org.freedesktop.DBus.StartServiceByName at /org/freedesktop/DBus
B-1: <- org.freedesktop.DBus return from C2
B-1: <- org.freedesktop.DBus return from C3
B-1: <- org.freedesktop.DBus return from C4
B-1: <- org.freedesktop.DBus return from C5
C6: -> org.freedesktop.DBus call org.freedesktop.DBus.GetNameOwner at /org/freedesktop/DBus
B-1: <- org.freedesktop.DBus return from C6
C7: -> :1.24 call org.freedesktop.Notifications.GetServerInformation at /org/freedesktop/Notifications
B78: <- :1.24 return from C7
C8: -> :1.24 call org.freedesktop.Notifications.GetServerInformation at /org/freedesktop/Notifications
B82: <- :1.24 return from C8
C9: -> :1.24 call org.freedesktop.Notifications.Notify at /org/freedesktop/Notifications
B85: <- :1.24 return from C9
"""


class TestDBusWizard(TestCase):
    def setUp(self) -> None:
        self.log_parser = DBusProxyLogParser()

    def feed_log_parse(self, lines: str) -> None:
        for line in lines.splitlines():
            self.log_parser.process_log_line(line)

    def test_parse_dbus_request_name(self) -> None:
        self.assertFalse(self.log_parser.wants_own_names)
        self.feed_log_parse(NAME_ACQUIRED_FAILED)
        self.assertIn("org.gnome.clocks", self.log_parser.wants_own_names)

    def test_parse_dbus_get_owner_name(self) -> None:
        self.assertFalse(self.log_parser.wants_talk_to)
        self.feed_log_parse(GET_OWNER_NAME_FAILED)
        self.assertIn("org.freedesktop.Notifications", self.log_parser.wants_talk_to)

    def test_parse_dbus_start_service_by_name(self) -> None:
        self.assertFalse(self.log_parser.wants_talk_to)
        self.feed_log_parse(START_SERVICE_BY_NAME_FAILED)
        self.assertIn("org.freedesktop.Notifications", self.log_parser.wants_talk_to)

    def test_parse_dbus_hidden_call(self) -> None:
        self.assertFalse(self.log_parser.wants_talk_to)
        self.feed_log_parse(HIDDEN_CALL)
        self.assertIn("org.freedesktop.Notifications", self.log_parser.wants_talk_to)

    def test_parse_no_errors(self) -> None:
        self.assertFalse(self.log_parser.wants_own_names)
        self.assertFalse(self.log_parser.wants_talk_to)
        self.feed_log_parse(NO_ERRORS)
        self.assertFalse(self.log_parser.wants_own_names)
        self.assertFalse(self.log_parser.wants_talk_to)
