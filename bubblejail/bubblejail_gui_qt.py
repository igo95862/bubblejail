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
from typing import Any, Iterator, List, Optional, Tuple, Type

from PyQt5.QtCore import QModelIndex
from PyQt5.QtWidgets import (QApplication, QCheckBox, QFormLayout, QGroupBox,
                             QHBoxLayout, QLabel, QLineEdit, QListWidget,
                             QListWidgetItem, QMainWindow, QPushButton,
                             QScrollArea, QVBoxLayout, QWidget)

from .bubblejail_directories import BubblejailDirectories
from .services import (BubblejailService, OptionBool, OptionSpaceSeparatedStr,
                       OptionStr, OptionStrList, ServiceOption,
                       ServiceOptionTypes)


class BubblejailGuiWidget:
    def __init__(self) -> None:
        self.widget = QWidget()

# region Config edit classes


class OptionWidgetBase(BubblejailGuiWidget):
    def __init__(
        self,
        name: str,
        description: str,
        data: ServiceOptionTypes,
    ):
        super().__init__()
        self.description = description
        self.name = name

    def get_data(self) -> ServiceOptionTypes:
        raise NotImplementedError


class OptionWidgetStrList(OptionWidgetBase):
    def __init__(
        self,
        name: str,
        description: str,
        data: List[str],
    ):
        super().__init__(
            name=name,
            description=description,
            data=data,
        )
        self.vertical_layout = QVBoxLayout()
        self.widget.setLayout(self.vertical_layout)

        # Header
        self.header = QLabel(self.name)
        self.header.setToolTip(self.description)
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
        if not data:
            self.add_line_edit()
        else:
            for string in data:
                self.add_line_edit(
                    existing_string=string,
                )

    def set_data(self, str_list: List[str]) -> None:
        for string in str_list:
            self.add_line_edit(
                existing_string=string
            )

    def remove_line_edit(self, line_edit_widget: QLineEdit) -> None:
        self.line_edit_widgets.remove(line_edit_widget)
        self.form_layout.removeRow(line_edit_widget)
        # HACK: add_button stops functioning if all rows get deleted
        # add empty row to prevent that.
        if not self.line_edit_widgets:
            self.add_line_edit()

    def add_line_edit(self, *args: List[Any],
                      existing_string: Optional[str] = None,) -> None:

        if isinstance(existing_string, str):
            # HACK: PyQt5 calls this function with bool when callsed by signal
            # to avoid passing bool to init check for str as existing string
            new_line_edit = QLineEdit(existing_string)
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
        return [maybe_empty for maybe_empty in text_list if maybe_empty]


class OptionWidgetBool(OptionWidgetBase):
    def __init__(
        self,
        name: str,
        description: str,
        data: bool,
    ):
        super().__init__(
            name=name,
            description=description,
            data=data,
        )
        self.widget = QCheckBox(name)
        self.widget.setToolTip(description)

        self.widget.setChecked(data)

    def get_data(self) -> bool:
        return bool(self.widget.isChecked())


class OptionWidgetStr(OptionWidgetBase):
    def __init__(
        self,
        name: str,
        description: str,
        data: str,
    ):
        super().__init__(
            name=name,
            description=description,
            data=data,
        )

        self.horizontal_layout = QHBoxLayout()
        self.widget.setLayout(self.horizontal_layout)

        self.label = QLabel(name)
        self.label.setToolTip(description)
        self.horizontal_layout.addWidget(self.label)

        self.line_edit = QLineEdit(data)
        self.line_edit.setToolTip(description)
        self.horizontal_layout.addWidget(self.line_edit)

    def get_data(self) -> str:
        return str(self.line_edit.text())


OptionToWidgetType = Tuple[ServiceOption, OptionWidgetBase]


class ServiceWidget:
    def __init__(self,
                 service: BubblejailService,
                 ):
        self.service = service

        self.group_widget = QGroupBox(service.pretty_name)
        self.group_widget.setToolTip(service.description)
        self.group_widget.setCheckable(True)
        self.group_widget.setChecked(service.enabled)

        # self.group_widget.setFlat(not is_options)

        self.group_layout = QVBoxLayout()
        self.group_widget.setLayout(self.group_layout)

        self.group_layout.addWidget(QLabel(service.description))

        def generator_option_widgets() -> Iterator[OptionToWidgetType]:
            for option in service.iter_options():
                if isinstance(option, OptionBool):
                    widget_class: Type[OptionWidgetBase] = OptionWidgetBool
                elif isinstance(option, (OptionStr, OptionSpaceSeparatedStr)):
                    widget_class = OptionWidgetStr
                elif isinstance(option, OptionStrList):
                    widget_class = OptionWidgetStrList
                else:
                    raise TypeError()

                new_widget = widget_class(
                    name=option.pretty_name,
                    description=option.description,
                    data=option.get_gui_value(),
                )

                self.group_layout.addWidget(new_widget.widget)

                yield option, new_widget

        self.option_to_widget_tuples = list(generator_option_widgets())

    def save(self) -> None:
        for option, option_widget in self.option_to_widget_tuples:
            option.set_value(option_widget.get_data())
        self.service.enabled = self.group_widget.isChecked()

# endregion Config edit classes

# region Central Widgets


class CentralWidgets:
    def __init__(self, parent: 'BubblejailConfigApp'):
        self.parent = parent
        self.widget = QWidget()


class InstanceEditWidget(CentralWidgets):
    def __init__(self,
                 parent: 'BubblejailConfigApp',
                 instance_name: str):
        super().__init__(parent=parent)

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
        save_button.clicked.connect(
            partial(InstanceEditWidget.set_instance_data, self))
        header.addWidget(save_button)

        self.main_layout.addLayout(header)

        self.scroll_area = QScrollArea()
        self.main_layout.addWidget(self.scroll_area)

        self.scroll_area.setWidgetResizable(True)
        self.scrolled_widget = QWidget()
        self.scrolled_layout = QVBoxLayout()
        self.scrolled_widget.setLayout(self.scrolled_layout)
        self.scroll_area.setWidget(self.scrolled_widget)

        # Instance
        self.bubblejail_instance = BubblejailDirectories.instance_get(
            instance_name)
        self.instance_config = self.bubblejail_instance. \
            _read_config()

        self.service_widgets: List[ServiceWidget] = []
        for service in self.instance_config.iter_services(
            iter_disabled=True,
            iter_default=False,
        ):
            new_service_widget = ServiceWidget(service)
            self.scrolled_layout.addWidget(new_service_widget.group_widget)
            self.service_widgets.append(new_service_widget)

    def set_instance_data(self) -> None:
        for service_widget in self.service_widgets:
            service_widget.save()

        from pprint import pprint
        pprint(self.instance_config.get_service_conf_dict())


class SelectInstanceWidget:
    def __init__(self, parent: 'BubblejailConfigApp'):
        self.parent = parent
        self.widget = QWidget()

        self.layout_vertical = QVBoxLayout()

        self.list_of_instances_widget = QListWidget()

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.list_of_instances_widget)

        self.layout_vertical.addWidget(self.scroll_area)

        self.list_of_instances_widget.clicked.connect(
            self.parent.switch_to_instance_edit)

        self.widget.setLayout(self.layout_vertical)

        # Create instance widgets
        for instance_path in BubblejailDirectories.iter_instances_path():
            new_list_item_widgets = QListWidgetItem(instance_path.stem)
            self.list_of_instances_widget.addItem(new_list_item_widgets)


# endregion Central Widgets


class BubblejailConfigApp:
    def __init__(self) -> None:
        self.q_app = QApplication(argv)
        self.window = QMainWindow()
        self.window.resize(600, 400)
        self.switch_to_selector()

    def switch_to_selector(self) -> None:
        container = SelectInstanceWidget(self)
        self.window.setCentralWidget(container.widget)

    def switch_to_instance_edit(self, qlist_item: QModelIndex) -> None:
        container = InstanceEditWidget(self, qlist_item.data())
        self.window.setCentralWidget(container.widget)

    def save_instance(self, instance_to_save: InstanceEditWidget) -> None:
        self.switch_to_selector()

    def run(self) -> None:
        self.window.show()
        self.q_app.exec()


def run_gui() -> None:
    BubblejailConfigApp().run()
