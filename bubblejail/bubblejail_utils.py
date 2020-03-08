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


from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Union, Set

from .services import SERVICES, BubblejailService

TypeServicesConfig = Dict[str, Dict[str, Union[str, List[str]]]]


@dataclass
class BubblejailInstanceConfig:
    """Represents config.toml"""
    executable_name: Optional[Union[str, List[str]]] = None
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


@dataclass
class ImportConfig:
    copy: List[Path] = field(default_factory=list)


@dataclass
class BubblejailProfile:
    config: Dict[str, Any] = field(default_factory=dict)
    dot_desktop_path: Optional[Path] = None
    import_conf: Optional[ImportConfig] = None
    gtk_application: bool = False

    def get_config(self) -> BubblejailInstanceConfig:
        return BubblejailInstanceConfig(**self.config)
