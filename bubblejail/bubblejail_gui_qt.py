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

from functools import partial
from sys import argv
from typing import List, Optional, Type

from PyQt5.QtCore import QModelIndex
from PyQt5.QtWidgets import (QApplication, QCheckBox, QFormLayout, QGroupBox,
                             QHBoxLayout, QLabel, QLineEdit, QListWidget,
                             QListWidgetItem, QMainWindow, QPushButton,
                             QVBoxLayout, QWidget, QScrollArea)

long_text = ('''aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
ccccccccccccccccccccccccccccccccccccc
dddddddddddddddddddddddddddddddddddddddddddddd''')


class SelectInstanceWidget:
    def __init__(self, parent: 'BubblejailConfigApp'):
        self.parent = parent
        self.widget = QWidget()

        self.layout_vertical = QVBoxLayout()

        list_of_instances_widget = QListWidget()

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(list_of_instances_widget)

        test_item = QListWidgetItem(parent=list_of_instances_widget)
        test_item.setText('Test')
        test_item2 = QListWidgetItem(parent=list_of_instances_widget)
        test_item2.setText('Test2')

        self.layout_vertical.addWidget(self.scroll_area)

        list_of_instances_widget.clicked.connect(
            self.parent.switch_to_instance_edit)

        self.widget.setLayout(self.layout_vertical)


class ListEditWidget:
    def __init__(self, parent: 'InstanceEditWidget'):
        self.parent = parent
        self.widget = QWidget()

        self.vertical_layout = QVBoxLayout()
        self.widget.setLayout(self.vertical_layout)

        self.form_layout = QFormLayout()
        self.line_edit_widgets: List[QLineEdit] = []
        self.vertical_layout.addLayout(self.form_layout)

        self.add_button = QPushButton('Add')
        self.vertical_layout.addWidget(self.add_button)
        self.add_button.clicked.connect(
            self.add_line_edit
        )

    def set_data(self, str_list: List[str]) -> None:
        for string in str_list:
            self.add_line_edit(string)

    def remove_line_edit(self, line_edit_widget: QLineEdit) -> None:
        self.line_edit_widgets.remove(line_edit_widget)
        self.form_layout.removeRow(line_edit_widget)

    def add_line_edit(self, existing_sting: Optional[str] = None,) -> None:
        if isinstance(existing_sting, str):
            # HACK: PyQt5 calls this function with bool when callsed by signal
            # to avoid passing bool to init check for str as existing string
            new_line_edit = QLineEdit(existing_sting)
        else:
            new_line_edit = QLineEdit('')

        self.line_edit_widgets.append(new_line_edit)

        new_push_button = QPushButton('❌')
        self.form_layout.addRow(new_line_edit, new_push_button)

        new_push_button.clicked.connect(
            partial(
                self.remove_line_edit, new_line_edit
            )
        )

    def get_data(self) -> List[str]:
        text_list = [x.text() for x in self.line_edit_widgets]
        return text_list


class InstanceEditWidget:
    def __init__(self, parent: 'BubblejailConfigApp'):
        self.parent = parent
        self.widget = QWidget()

        self.main_layout = QVBoxLayout()
        self.widget.setLayout(self.main_layout)

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

        self.scroll_area = QScrollArea()
        self.main_layout.addWidget(self.scroll_area)

        self.scroll_area.setWidgetResizable(True)
        self.scrolled_widget = QWidget()
        self.scrolled_layout = QVBoxLayout()
        self.scrolled_widget.setLayout(self.scrolled_layout)
        self.scroll_area.setWidget(self.scrolled_widget)

        # Groups
        self.scrolled_layout.addWidget(QLabel('General Options'))

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

        test_list_edit = self.add_list_edit(
            parent_layout=general_group_layout
        )
        test_list_edit.set_data(['test1', 'test2', ';124134'])

    def add_group_return_layout(
            self, title: str, is_checkable: bool) -> QVBoxLayout:
        new_group = QGroupBox(title)
        new_group.setCheckable(is_checkable)
        group_layout = QVBoxLayout()
        new_group.setLayout(group_layout)
        self.scrolled_layout.addWidget(new_group)
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

    def add_list_edit(self, parent_layout: QVBoxLayout) -> ListEditWidget:
        new_list_edit = ListEditWidget(self)
        parent_layout.addWidget(new_list_edit.widget)
        return new_list_edit


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
