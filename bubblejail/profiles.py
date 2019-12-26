from dataclasses import dataclass, field
from typing import List
from pathlib import Path


@dataclass
class BubblejailBaseProfile:
    import_paths: List[str] = field(default_factory=list)


FIREFOX_PROFILE = BubblejailBaseProfile(
    import_paths=[f'{Path.home()}/.mozzila/firefox'])

__all__ = ["FIREFOX_PROFILE"]
