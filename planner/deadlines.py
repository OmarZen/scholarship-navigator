"""
Deadline resolution: turns a scholarship's deadline pattern into a concrete date for the
candidate's intake year, preferring confirmed dates (user-verified or published) over estimates.
"""

import calendar
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional, Tuple

from .models import Scholarship, ApplicationState, DeadlinePattern


@dataclass
class DeadlineInfo:
    date: Optional[date]
    is_estimate: bool = True
    precision: str = "approx"
    label: str = "Not set"
    source: Optional[str] = None
    next_cycle: Optional[date] = None
    extras: List[Tuple[str, date]] = field(default_factory=list)

    @property
    def display(self) -> str:
        if not self.date:
            return "Unknown"
        suffix = " (est.)" if self.is_estimate else ""
        return f"{self.date.isoformat()}{suffix}"


def safe_date(year: int, month: int, day: int) -> date:
    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(day, last))


def pattern_date(p: DeadlinePattern, intake_year: int) -> date:
    return safe_date(intake_year - p.years_before_intake, p.month, p.day)


def resolve_deadline(
    scholarship: Scholarship,
    intake_year: int,
    today: date,
    state: Optional[ApplicationState] = None,
    override: Optional[DeadlineInfo] = None,
) -> DeadlineInfo:
    """Priority: date confirmed by the candidate > chosen-program deadline (override) > published date > pattern."""
    est = scholarship.timeline.deadline

    if override and override.date and not (state and state.deadline_confirmed):
        info = override
    elif state and state.deadline_confirmed:
        info = DeadlineInfo(
            date=state.deadline_confirmed,
            is_estimate=False,
            precision="exact",
            label="Confirmed by you",
            source=state.deadline_source,
        )
    elif est and est.known_dates.get(str(intake_year)):
        info = DeadlineInfo(
            date=date.fromisoformat(est.known_dates[str(intake_year)]),
            is_estimate=False,
            precision="exact",
            label=est.label or "Published date",
            source=est.source,
        )
    elif est:
        info = DeadlineInfo(
            date=pattern_date(est, intake_year),
            is_estimate=True,
            precision=est.precision,
            label=(est.label or "Estimated from usual pattern"),
            source=est.source,
        )
    else:
        return DeadlineInfo(date=None)

    if est:
        info.extras = [(x.label or "Other date", pattern_date(x, intake_year)) for x in est.extra]

    if info.date and info.date < today and est:
        nxt = est.known_dates.get(str(intake_year + 1))
        info.next_cycle = date.fromisoformat(nxt) if nxt else pattern_date(est, intake_year + 1)

    return info
