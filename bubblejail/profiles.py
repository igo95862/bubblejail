from dataclasses import dataclass, field
from typing import List, Dict
from pathlib import Path
from .services import X11
from .bwrap_config import BwrapArgs


@dataclass
class BubblejailBaseProfile:
    executable_name: str
    import_paths: List[str] = field(default_factory=list)
    services: List[BwrapArgs] = field(default_factory=list)

    def generate_bw_args(self) -> BwrapArgs:
        new_args = BwrapArgs()
        for x in self.services:
            new_args.extend(x)
        return new_args


FIREFOX_PROFILE = BubblejailBaseProfile(
    import_paths=[f'{Path.home()}/.mozzila/firefox'],
    services=[X11],
    executable_name='firefox',)

applications: Dict[str, BubblejailBaseProfile] = {
    'firefox': FIREFOX_PROFILE,
}

__all__ = ["FIREFOX_PROFILE"]
