from dataclasses import dataclass, field
from typing import List


@dataclass
class BubblejailBaseProfile:
    import_paths: List[str] = field(default_factory=list)
