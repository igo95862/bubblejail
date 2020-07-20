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
from typing import Any, Dict, List, Optional, Type, Union

from PyQt5.QtCore import QModelIndex
from PyQt5.QtWidgets import (QApplication, QCheckBox, QFormLayout, QGroupBox,
                             QHBoxLayout, QLabel, QLineEdit, QListWidget,
                             QListWidgetItem, QMainWindow, QPushButton,
                             QScrollArea, QVBoxLayout, QWidget)

from .bubblejail_utils import TypeServicesConfig
from .services import ServiceInfo, ServiceOptionInfo

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


class BubblejailGuiWidget:
    def __init__(self) -> None:
        self.widget = QWidget()

# region Config edit classes


class ConfigEditBase(BubblejailGuiWidget):
    def get_data(self) -> Union[str, bool, List[str]]:
        raise NotImplementedError


class ConfigStrList(ConfigEditBase):
    def __init__(
        self,
        name: str,
        description: str,
    ):
        super().__init__()
        self.description = description
        self.vertical_layout = QVBoxLayout()
        self.widget.setLayout(self.vertical_layout)

        # Header
        self.header = QLabel(name)
        self.header.setToolTip(description)
        self.vertical_layout.addWidget(self.header)

        self.form_widget = QWidget()
        self.form_layout: QFormLayout = QFormLayout()
        self.form_widget.setLayout(self.form_layout)
        self.vertical_layout.addWidget(self.form_widget)

        self.line_edit_widgets: List[QLineEdit] = []

        self.add_button = QPushButton('Add')
        self.add_button.setToolTip(self.description)
        self.vertical_layout.addWidget(self.add_button)
        self.add_button.clicked.connect(
            self.add_line_edit
        )

    def set_data(self, str_list: List[str]) -> None:
        for string in str_list:
            self.add_line_edit(
                existing_sting=string
            )

    def remove_line_edit(self, line_edit_widget: QLineEdit) -> None:
        self.line_edit_widgets.remove(line_edit_widget)
        self.form_layout.removeRow(line_edit_widget)
        # HACK: add_button stops functioning if all rows get deleted
        # add empty row to prevent that.
        if not self.line_edit_widgets:
            self.add_line_edit()

    def add_line_edit(self, *args: List[Any],
                      existing_sting: Optional[str] = None,) -> None:

        if isinstance(existing_sting, str):
            # HACK: PyQt5 calls this function with bool when callsed by signal
            # to avoid passing bool to init check for str as existing string
            new_line_edit = QLineEdit(existing_sting)
        else:
            new_line_edit = QLineEdit('')

        new_line_edit.setToolTip(self.description)

        self.line_edit_widgets.append(new_line_edit)

        new_push_button = QPushButton('❌')

        self.form_layout.addRow(new_push_button, new_line_edit)

        new_push_button.clicked.connect(
            partial(
                self.remove_line_edit, new_line_edit
            )
        )

    def get_data(self) -> List[str]:
        text_list = [x.text() for x in self.line_edit_widgets]
        return text_list


class ConfigBool(ConfigEditBase):
    def __init__(
        self,
        name: str,
        description: str,
    ):
        super().__init__()
        self.widget = QCheckBox(name)
        self.widget.setToolTip(description)


class ConfigStr(ConfigEditBase):
    def __init__(
        self,
        name: str,
        description: str,
    ):
        super().__init__()
        self.horizontal_layout = QHBoxLayout()
        self.widget.setLayout(self.horizontal_layout)

        self.label = QLabel(name)
        self.label.setToolTip(description)
        self.horizontal_layout.addWidget(self.label)

        self.line_edit = QLineEdit()
        self.line_edit.setToolTip(description)
        self.horizontal_layout.addWidget(self.line_edit)


# endregion Config edit classes


class SettingsGroup:
    def __init__(self,
                 parent: 'InstanceEditWidget',
                 service_info: ServiceInfo,
                 is_options: bool = True):
        self.group_widget = QGroupBox(service_info.name)
        self.group_widget.setToolTip(service_info.description)

        self.group_widget.setCheckable(is_options)
        self.group_widget.setFlat(not is_options)

        self.group_layout = QVBoxLayout()
        self.group_widget.setLayout(self.group_layout)

        self.service_info = service_info
        self.option_name_to_widget_dict: Dict[str, ConfigEditBase] = {}

        # Parse options
        for option_name, option_info in service_info.options.items():
            if option_info.typing is bool:
                new_widget: ConfigEditBase = ConfigBool(
                    name=option_info.name,
                    description=option_info.description,
                )
            elif option_info.typing is str:
                new_widget = ConfigStr(
                    name=option_info.name,
                    description=option_info.description,
                )
            elif option_info.typing is List[str]:
                new_widget = ConfigStrList(
                    name=option_info.name,
                    description=option_info.description,
                )
            else:
                raise TypeError('Unknown service option type')

            self.option_name_to_widget_dict[option_name] = new_widget
            self.group_layout.addWidget(new_widget.widget)

    def to_dict(self) -> TypeServicesConfig:
        ...


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
        test_service = ServiceInfo(
            name='test',
            description=long_text,
            options={
                'test_checkbox': ServiceOptionInfo(
                    name='Test checkbox',
                    description='Test Option text',
                    typing=bool,
                ),
                'test_linedit': ServiceOptionInfo(
                    name='Test line edit',
                    description='Test 2 Option text',
                    typing=str,
                ),
                'test_lines_edit': ServiceOptionInfo(
                    name='Test multi line edit',
                    description='Test 3 Option text',
                    typing=List[str],
                ),
            }
        )
        group = self.add_group_return_layout(True, test_service)
        t = group.option_name_to_widget_dict['test_lines_edit']
        if isinstance(t, ConfigStrList):
            t.set_data(['test', 'testaetgas'])

    def add_group_return_layout(
        self,
        is_checkable: bool,
        service_info: ServiceInfo,
    ) -> SettingsGroup:
        new_settings = SettingsGroup(
            parent=self,
            service_info=service_info,
            is_options=is_checkable,
        )
        self.scrolled_layout.addWidget(new_settings.group_widget)
        return new_settings

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

    def save_instance(self, instance_to_save: InstanceEditWidget) -> None:
        print()
        self.switch_to_selector()

    def run(self) -> None:
        self.window.show()
        self.q_app.exec()


def run_gui() -> None:
    BubblejailConfigApp().run()
