"""
Credential Legalization & Equivalence Navigator.
Provides step-by-step procedures for Uni-Assist (Germany), CIMEA / DoV (Italy),
WES (USA/Canada), and Hague Apostille / Consular Legalization.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional


def load_credential_guides(data_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    if data_path is None:
        data_path = Path(__file__).parent.parent / "data" / "credential_guides.json"
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_credential_guide_for_country(country_name: str) -> Optional[Dict[str, Any]]:
    guides = load_credential_guides()
    query = country_name.strip().lower()
    for g in guides:
        if query in g["country"].lower() or g["country"].lower() in query:
            return g
    # Fallback to Apostille guide if country not explicitly found
    return guides[3]

