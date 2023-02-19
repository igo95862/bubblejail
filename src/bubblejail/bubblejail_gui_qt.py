# SPDX-License-Identifier: GPL-3.0-or-later

# Copyright 2019-2022 igo95862

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
from __future__ import annotations

from functools import partial
from sys import argv
from typing import Any, Iterator, List, Optional, Tuple, Type

from PyQt6.QtCore import QModelIndex
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .bubblejail_directories import BubblejailDirectories
from .bubblejail_instance import BubblejailProfile
from .exceptions import BubblejailInstanceNotFoundError
from .services import (
    BubblejailService,
    OptionBool,
    OptionSpaceSeparatedStr,
    OptionStr,
    OptionStrList,
    ServiceOptionTypes,
)


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
        bubblejail_service_name: str,
    ):
        super().__init__()
        self.description = description
        self.name = name
        self.bubblejail_service_name = bubblejail_service_name

    def get_data(self) -> ServiceOptionTypes:
        raise NotImplementedError


class OptionWidgetStrList(OptionWidgetBase):
    def __init__(
        self,
        name: str,
        description: str,
        data: List[str],
        bubblejail_service_name: str,
    ):
        super().__init__(
            name=name,
            description=description,
            data=data,
            bubblejail_service_name=bubblejail_service_name,
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
        bubblejail_service_name: str,
    ):
        super().__init__(
            name=name,
            description=description,
            data=data,
            bubblejail_service_name=bubblejail_service_name,
        )
        self.widget = QCheckBox(name)
        self.widget.setToolTip(description)

        self.widget.setChecked(data)

    def get_data(self) -> bool:
        assert isinstance(self.widget, QCheckBox)
        return bool(self.widget.isChecked())


class OptionWidgetStr(OptionWidgetBase):
    def __init__(
        self,
        name: str,
        description: str,
        data: str,
        bubblejail_service_name: str,
    ):
        super().__init__(
            name=name,
            description=description,
            data=data,
            bubblejail_service_name=bubblejail_service_name,
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


class OptionWidgetCombobox(OptionWidgetBase):
    def __init__(
        self,
        name: str,
        description: str,
        bubblejail_service_name: str,
    ):
        super().__init__(
            name=name,
            description=description,
            data='None',
            bubblejail_service_name=bubblejail_service_name,
        )
        self.horizontal_layout = QHBoxLayout()
        self.widget.setLayout(self.horizontal_layout)

        self.label = QLabel(name)
        self.label.setToolTip(description)

        self.horizontal_layout.addWidget(self.label)
        self.combobox = QComboBox()
        self.combobox.setToolTip(description)
        self.horizontal_layout.addWidget(self.combobox)
        self.combobox.addItem('None')

    def add_item(self, new_item: str) -> None:
        self.combobox.addItem(new_item)

    def get_data(self) -> str:
        return str(self.combobox.currentText())


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

        self.option_widgets: list[OptionWidgetBase] = []

        for option in service.iter_options():
            if option.is_deprecated:
                continue

            if isinstance(option, OptionBool):
                widget_class: Type[OptionWidgetBase] = OptionWidgetBool
            elif isinstance(option, (OptionStr, OptionSpaceSeparatedStr)):
                widget_class = OptionWidgetStr
            elif isinstance(option, OptionStrList):
                widget_class = OptionWidgetStrList
            else:
                raise TypeError

            new_widget = widget_class(
                name=option.pretty_name,
                description=option.description,
                data=option.get_gui_value(),
                bubblejail_service_name=option.name,
            )

            self.group_layout.addWidget(new_widget.widget)

            self.option_widgets.append(new_widget)

    def disable(self, message: str) -> None:
        self.group_widget.setChecked(False)
        self.group_widget.setCheckable(False)
        self.group_widget.setTitle(message)
        self.group_widget.update()

    def enable(self) -> None:
        if self.group_widget.isCheckable():
            return

        self.group_widget.setTitle(self.service.pretty_name)
        self.group_widget.setCheckable(True)
        self.group_widget.setChecked(False)
        self.group_widget.update()

    def bubblejail_read_service_dict(self) -> dict[str, Any]:
        return {
            widget.bubblejail_service_name: widget.get_data()
            for widget
            in self.option_widgets
        }

# endregion Config edit classes

# region Central Widgets


class CentralWidgets:
    def __init__(self, parent: BubblejailConfigApp):
        self.parent = parent
        self.widget = QWidget()


class InstanceEditWidget(CentralWidgets):
    def __init__(self,
                 parent: BubblejailConfigApp,
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
        header_label = QLabel(f"Editing {instance_name}")
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

            new_service_widget.group_widget.clicked.connect(
                partial(
                    InstanceEditWidget.refresh_conflicts, self,
                )
            )

        self.refresh_conflicts(True)

    def set_instance_data(self) -> None:
        new_config = {
            x.service.name: x.bubblejail_read_service_dict()
            for x in self.service_widgets
            if x.group_widget.isChecked()
        }
        self.instance_config.set_services(new_config)

        self.bubblejail_instance.save_config(self.instance_config)
        self.parent.switch_to_selector()

    def refresh_conflicts(self, new_state: bool) -> None:
        enabled_conflicts: set[str] = set()

        for service_widget in self.service_widgets:
            if service_widget.group_widget.isChecked():

                enabled_conflicts |= service_widget.service.conflicts

        for service_widget in self.service_widgets:

            if service_widget.service.name in enabled_conflicts:
                service_widget.disable(
                    f"⚠ Service {service_widget.service.name} conflicts with "
                    f"{', '.join(service_widget.service.conflicts)}. ⚠"
                )
            else:
                service_widget.enable()


class CreateInstanceWidget(CentralWidgets):
    def __init__(self,
                 parent: BubblejailConfigApp,
                 ):
        super().__init__(parent=parent)

        self.main_layout = QVBoxLayout()
        self.widget.setLayout(self.main_layout)

        header = QHBoxLayout()
        # Back button
        back_button = QPushButton('Back')
        back_button.clicked.connect(self.parent.switch_to_selector)
        header.addWidget(back_button)

        # Save button
        self.save_button = QPushButton('Create')
        self.save_button.clicked.connect(
            partial(CreateInstanceWidget.create_instance, self))
        header.addWidget(self.save_button)

        self.main_layout.addLayout(header)

        self.name_widget = OptionWidgetStr(
            name='Instance name',
            description='Name with which the instance will be created',
            data='',
            bubblejail_service_name='',
        )
        self.main_layout.addWidget(self.name_widget.widget)

        self.profile_select_widget = OptionWidgetCombobox(
            name='Select profile:',
            description='Select profile to create instance with.',
            bubblejail_service_name='',
        )
        self.main_layout.addWidget(self.profile_select_widget.widget)
        self.profile_select_widget.combobox.textActivated.connect(
            self.selection_changed)

        self.name_widget.line_edit.textChanged.connect(
            self.refresh_create_button
        )

        self.profile_text = QLabel('No profile selected')
        self.main_layout.addWidget(self.profile_text)

        self.current_profile: Optional[BubblejailProfile] = None

        profiles_names = set()
        for profiles_directory in \
                BubblejailDirectories.iter_profile_directories():
            for profile_file in profiles_directory.iterdir():
                profiles_names.add(profile_file.stem)

        for profile_name in profiles_names:
            self.profile_select_widget.add_item(profile_name)

        self.refresh_create_button()

    def can_be_created(self) -> Tuple[bool, str]:
        current_name = self.name_widget.get_data()
        if not current_name:
            return False, '⚠ Name is empty'
        else:
            try:
                BubblejailDirectories.instance_get(current_name)
                return False, '⚠ Name is already used'
            except BubblejailInstanceNotFoundError:
                ...

        if self.current_profile is not None:
            if self.current_profile.dot_desktop_path is not None and \
                    not self.current_profile.dot_desktop_path.is_file():
                warn_text = (
                    '⚠ WARNING \n'
                    'Desktop entry does not exist\n'
                    'Maybe you don\'t have application installed?'
                )
                return False, warn_text
            else:
                return True, (
                    f"{self.current_profile.description}\n"
                    f"Import tips:  {self.current_profile.import_tips}"
                )

        return True, 'Create empty profile'

    def refresh_create_button(self) -> None:
        is_allowed, new_text = self.can_be_created()

        self.save_button.setEnabled(is_allowed)
        self.profile_text.setText(new_text)

    def selection_changed(self, new_text: str) -> None:
        if new_text == 'None':
            self.current_profile = None
        else:
            self.current_profile = BubblejailDirectories.profile_get(new_text)
            if self.current_profile is not None and \
                    self.current_profile.dot_desktop_path is not None:
                self.name_widget.line_edit.setText(
                    self.current_profile.dot_desktop_path.stem
                )

        self.refresh_create_button()

    def create_instance(self) -> None:
        new_instance_name = self.name_widget.get_data()
        if not new_instance_name:
            raise RuntimeError('No instance name given')
        profile_name: Optional[str] = self.profile_select_widget.get_data()
        if profile_name == 'None':
            profile_name = None

        BubblejailDirectories.create_new_instance(
            new_name=new_instance_name,
            profile_name=profile_name,
            create_dot_desktop=True,
        )
        self.parent.switch_to_selector()


class SelectInstanceWidget:
    def __init__(self, parent: BubblejailConfigApp):
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
            new_list_item_widgets = QListWidgetItem(instance_path.name)
            self.list_of_instances_widget.addItem(new_list_item_widgets)

        # Create button
        self.create_button = QPushButton('Create instance')
        self.layout_vertical.addWidget(self.create_button)
        self.create_button.clicked.connect(
            self.parent.switch_to_create_instance)


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

    def switch_to_create_instance(self) -> None:
        container = CreateInstanceWidget(self)
        self.window.setCentralWidget(container.widget)

    def save_instance(self, instance_to_save: InstanceEditWidget) -> None:
        self.switch_to_selector()

    def run(self) -> None:
        self.window.show()
        self.q_app.exec()


def run_gui() -> None:
    BubblejailConfigApp().run()
