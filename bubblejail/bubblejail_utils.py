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


from dataclasses import dataclass, field, InitVar
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Set, Union

from .bwrap_config import BwrapConfigBase, DbusSessionTalkTo
from .services import SERVICES, BubblejailService

TypeServicesConfig = Dict[str, Dict[str, Union[str, List[str]]]]


@dataclass
class BubblejailInstanceConfig:
    """Represents config.toml"""
    executable_name: Optional[Union[str, List[str]]] = None
    share_local_time: bool = True
    services: List[str] = field(default_factory=list)
    service: TypeServicesConfig = field(default_factory=dict)

    def iter_services(self) -> Generator[BubblejailService, None, None]:
        initialized_services_names: Set[str] = set()

        for service_name, service_dict in self.service.items():
            initialized_services_names.add(service_name)
            yield SERVICES[service_name](**service_dict)

        for service_name in self.services:
            if service_name not in initialized_services_names:
                yield SERVICES[service_name]()

    def verify(self) -> None:
        for service in self.iter_services():
            for arg in service:
                if isinstance(arg, BwrapConfigBase):
                    arg.to_args()
                elif isinstance(arg, DbusSessionTalkTo):
                    arg.to_args()
                else:
                    ...


@dataclass
class ImportConfig:
    copy: List[Path] = field(default_factory=list)


@dataclass
class BubblejailProfile:
    dot_desktop_path: Optional[Path] = None
    config: Dict[str, Any] = field(default_factory=dict)
    import_conf: InitVar[ImportConfig] = None
    gtk_application: bool = False

    def __post_init__(self,
                      import_conf: Union[ImportConfig, Dict[str, Any], None],
                      ) -> None:
        if isinstance(import_conf, ImportConfig):
            self.import_conf = import_conf
        elif isinstance(import_conf, dict):
            self.import_conf = ImportConfig(**import_conf)
        elif import_conf is None:
            self.import_conf = ImportConfig()
        else:
            raise TypeError(f'Wrong import conf type: {import_conf}')

    def get_config(self) -> BubblejailInstanceConfig:
        return BubblejailInstanceConfig(**self.config)
