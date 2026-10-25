"""
Country normalization and country-group membership (Africa, DAC list, EU/EEA, ...).
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Set

REGIONS_PATH = Path(__file__).parent.parent / "data" / "regions.json"


@lru_cache(maxsize=1)
def _load() -> Dict:
    with open(REGIONS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _key(name: str) -> str:
    return " ".join(name.strip().lower().replace("’", "'").split())


@lru_cache(maxsize=1)
def _canonical_names() -> Dict[str, str]:
    names: Dict[str, str] = {}
    for group in _load()["groups"].values():
        for c in group.get("countries", []) + group.get("ambiguous", []):
            names[_key(c)] = c
    for alias, canonical in _load()["aliases"].items():
        names[_key(alias)] = canonical
        names.setdefault(_key(canonical), canonical)
    return names


def normalize_country(name: Optional[str]) -> str:
    if not name:
        return ""
    return _canonical_names().get(_key(name), name.strip())


def same_country(a: Optional[str], b: Optional[str]) -> bool:
    return bool(a) and bool(b) and _key(normalize_country(a)) == _key(normalize_country(b))


@lru_cache(maxsize=None)
def group_members(group_id: str) -> frozenset:
    groups = _load()["groups"]
    group = groups.get(group_id)
    if not group:
        return frozenset()
    members: Set[str] = {_key(normalize_country(c)) for c in group.get("countries", [])}
    for sub in group.get("include_groups", []):
        members |= set(group_members(sub))
    return frozenset(members)


def group_ambiguous(group_id: str) -> Set[str]:
    group = _load()["groups"].get(group_id, {})
    return {_key(normalize_country(c)) for c in group.get("ambiguous", [])}


def in_group(country: str, group_id: str) -> Optional[bool]:
    """True / False, or None when the country sits on the group's fuzzy border."""
    k = _key(normalize_country(country))
    if k in group_members(group_id):
        return True
    if k in group_ambiguous(group_id):
        return None
    return False


def in_list(country: str, countries: List[str]) -> bool:
    k = _key(normalize_country(country))
    return any(_key(normalize_country(c)) == k for c in countries)


def group_title(group_id: str) -> str:
    return _load()["groups"].get(group_id, {}).get("title", group_id)
