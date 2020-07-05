# SPDX-License-Identifier: GPL-3.0-or-later

# Copyright 2019, 2020 igo95862

# This file is part of bubblejail.
# bubblejail is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# bubblejail is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with bubblejail.  If not, see <https://www.gnu.org/licenses/>.

from sys import argv

from PyQt5.QtCore import QModelIndex
from PyQt5.QtWidgets import (QApplication, QHBoxLayout, QListWidget,
                             QListWidgetItem, QMainWindow, QPushButton,
                             QVBoxLayout, QWidget)


class SelectInstanceWidget:
    def __init__(self, parent: 'BubblejailConfigApp'):
        self.parent = parent
        self.widget = QWidget()

        layout_vertical = QVBoxLayout()

        list_of_instances_widget = QListWidget()

        test_item = QListWidgetItem(parent=list_of_instances_widget)
        test_item.setText('Test')
        test_item2 = QListWidgetItem(parent=list_of_instances_widget)
        test_item2.setText('Test2')

        layout_vertical.addWidget(list_of_instances_widget)

        list_of_instances_widget.clicked.connect(
            self.parent.switch_to_instance_edit)

        self.widget.setLayout(layout_vertical)


class InstanceEditWidget:
    def __init__(self, parent: 'BubblejailConfigApp'):
        self.parent = parent
        self.widget = QWidget()

        bottom_pannel = QHBoxLayout()
        test_button = QPushButton('Top')
        test_button.clicked.connect(self.parent.switch_to_selector)

        bottom_pannel.addWidget(test_button)
        bottom_pannel.addWidget(QPushButton('Bottom'))

        self.widget.setLayout(bottom_pannel)


class BubblejailConfigApp:
    def __init__(self) -> None:
        self.q_app = QApplication(argv)
        self.window = QMainWindow()
        self.switch_to_selector()

    def switch_to_selector(self) -> None:
        container = SelectInstanceWidget(self)
        self.window.setCentralWidget(container.widget)

    def switch_to_instance_edit(self, instance_widget: QModelIndex) -> None:
        container = InstanceEditWidget(self)
        self.window.setCentralWidget(container.widget)

    def run(self) -> None:
        self.window.show()
        self.q_app.exec()


def run_gui() -> None:
    BubblejailConfigApp().run()
