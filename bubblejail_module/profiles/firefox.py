from .base_profile import BubblejailBaseProfile
from pathlib import Path

FIREFOX_PROFILE = BubblejailBaseProfile(
    import_paths=[f'{Path.home()}/.mozzila/firefox'])

__all__ = ["FIREFOX_PROFILE"]
