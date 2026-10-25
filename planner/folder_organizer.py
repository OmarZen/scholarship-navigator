"""
Local Application Dossier & Document Organizer.

Kept for backward compatibility: creates a full candidate workspace (see planner/workspace.py) at the given folder.
"""

from pathlib import Path
from typing import List, Optional

from .models import CandidateProfile, MatchResult
from .workspace import create_workspace, build_workspace


def initialize_application_workspace(profile: CandidateProfile, matches: Optional[List[MatchResult]], target_dir: str) -> str:
    target = Path(target_dir)
    ws = create_workspace(profile.model_dump(mode="json"), root=target.parent, name=target.name)
    build_workspace(ws)
    return str(ws.resolve())
