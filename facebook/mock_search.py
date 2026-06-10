"""
Mock Facebook profile lookup.

Uses a deterministic hash of the employee name so the same name always
returns the same profile — useful for demos and testing.

Replace the body of `search_facebook_profile` with real scraping/API
calls once legal access is available.
"""

import hashlib
from .profile import FacebookProfile

_FRIENDS_OPTIONS = [0, 2, 5, 8, 15, 35, 100, 250, 500, 800]
_POSTS_OPTIONS   = [0, 1, 3, 6, 12, 25, 50, 120]
_PPH_OPTIONS     = [0.0, 0.5, 1.0, 2.0, 5.0, 8.0, 10.0, 15.0, 20.0]


def search_facebook_profile(employee_name: str) -> FacebookProfile:
    """Return a mock FacebookProfile derived deterministically from the name."""
    raw = hashlib.sha256(employee_name.lower().strip().encode()).digest()
    n = int.from_bytes(raw, "big")

    def _bit(pos: int) -> bool:
        return bool((n >> pos) & 1)

    def _pick(options: list, offset: int):
        return options[(n >> offset) % len(options)]

    return FacebookProfile(
        has_profile_picture=_bit(0),
        friends_count=_pick(_FRIENDS_OPTIONS, 4),
        posts_count=_pick(_POSTS_OPTIONS, 8),
        has_basic_info=_bit(12),
        suspicious_name=_bit(13),
        low_interactions=_bit(14),
        no_mutual_connections=_bit(15),
        employee_info_match=_bit(16),
        posts_per_hour=_pick(_PPH_OPTIONS, 20),
    )
