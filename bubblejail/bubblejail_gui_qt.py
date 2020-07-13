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
from typing import Optional, Type

from PyQt5.QtCore import QModelIndex
from PyQt5.QtWidgets import (QApplication, QCheckBox, QGroupBox, QHBoxLayout,
                             QLabel, QLineEdit, QListWidget, QListWidgetItem,
                             QMainWindow, QPushButton, QVBoxLayout, QWidget)

long_text = ('''aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
ccccccccccccccccccccccccccccccccccccc
dddddddddddddddddddddddddddddddddddddddddddddd''')


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

        self.main_layout = QVBoxLayout()

        header = QHBoxLayout()
        # Back button
        back_button = QPushButton('Back')
        back_button.clicked.connect(self.parent.switch_to_selector)
        header.addWidget(back_button)
        # Label
        header_label = QLabel('Editing ...')
        header.addWidget(header_label)
        # Save button
        save_button = QPushButton('Save')
        header.addWidget(save_button)

        self.main_layout.addLayout(header)

        # Groups
        self.main_layout.addWidget(QLabel('General Options'))

        general_group_layout = self.add_group_return_layout(
            title='Test Group',
            is_checkable=True
        )

        self.add_checkbox(
            'Test',
            general_group_layout,
            tooltip_text=long_text,
        )
        self.add_line_edit(
            'Test',
            general_group_layout,
            tooltip_text=long_text,
        )

        self.widget.setLayout(self.main_layout)

    def add_group_return_layout(
            self, title: str, is_checkable: bool) -> QVBoxLayout:
        new_group = QGroupBox(title)
        new_group.setCheckable(is_checkable)
        group_layout = QVBoxLayout()
        new_group.setLayout(group_layout)
        self.main_layout.addWidget(new_group)
        return group_layout

    def add_widget_return_widget(
        self,
        widget_class: Type[QWidget],
        text: str,
        parent_layout: QVBoxLayout,
        tooltip_text: Optional[str] = None,
    ) -> QWidget:
        new_widget = widget_class(text)

        if tooltip_text is not None:
            new_widget.setToolTip(tooltip_text)

        parent_layout.addWidget(new_widget)

        return new_widget

    def add_checkbox(
        self,
        text: str,
        parent_layout: QVBoxLayout,
        tooltip_text: Optional[str] = None,
    ) -> QCheckBox:
        return self.add_widget_return_widget(
            widget_class=QCheckBox,
            text=text,
            parent_layout=parent_layout,
            tooltip_text=tooltip_text,
        )

    def add_line_edit(
        self,
        text: str,
        parent_layout: QVBoxLayout,
        tooltip_text: Optional[str] = None,
    ) -> QLineEdit:
        return self.add_widget_return_widget(
            widget_class=QLineEdit,
            text=text,
            parent_layout=parent_layout,
            tooltip_text=tooltip_text,
        )


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
