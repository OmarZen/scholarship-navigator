"""
Application Portfolio Risk Optimizer & Strategic Balancer.
Groups open, eligible scholarships into Reach / Target / Safety tiers (tier comes from data/scholarships.json),
suggests a balanced set to apply to, and gives a rough chance of winning at least one.

The odds are a heuristic (fixed base rates per tier, adjusted by your fit score), not real admission statistics.
"""

from typing import Any, Dict, List

from .models import CandidateProfile, MatchResult
from .roadmap import INACTIVE_TIMELINES

BASE_PROBABILITIES = {"Reach": 0.04, "Target": 0.15, "Safety": 0.40}
CAPS = {"Reach": 0.12, "Target": 0.35, "Safety": 0.70}
PORTFOLIO_SHAPE = {"Reach": 2, "Target": 3, "Safety": 2}
TIER_LABEL = {"Reach": "Reach (Dream Tier)", "Target": "Target (Strong Match)", "Safety": "Safety / High Probability"}


def categorize_scholarship(m: MatchResult) -> str:
    return TIER_LABEL[m.tier]


def _win_probability(m: MatchResult) -> float:
    fit_mod = 0.6 + 0.8 * (m.fit_score / 100.0)  # fit 50 -> 1.0x, fit 100 -> 1.4x
    return min(CAPS[m.tier], BASE_PROBABILITIES[m.tier] * fit_mod)


def analyze_application_portfolio(profile: CandidateProfile, matches: List[MatchResult]) -> Dict[str, Any]:
    active = [m for m in matches if m.is_eligible and m.readiness and m.readiness.timeline_status not in INACTIVE_TIMELINES]
    active.sort(key=lambda m: -m.priority_score)
    tiers: Dict[str, List[MatchResult]] = {"Reach": [], "Target": [], "Safety": []}
    for m in active:
        tiers[m.tier].append(m)

    def item(m: MatchResult) -> Dict[str, Any]:
        return {"id": m.scholarship.id, "name": m.scholarship.name, "country": m.scholarship.country,
                "match_score": m.fit_score, "readiness": m.readiness_percent, "funding": m.scholarship.funding_type,
                "deadline": m.readiness.deadline.isoformat() if m.readiness and m.readiness.deadline else None,
                "win_probability": round(100 * _win_probability(m), 1)}

    selected = [m for tier, n in PORTFOLIO_SHAPE.items() for m in tiers[tier][:n]]
    fail = 1.0
    for m in selected:
        fail *= 1.0 - _win_probability(m)
    success = round((1.0 - fail) * 100.0, 1)

    recommendations = []
    if not tiers["Safety"]:
        recommendations.append("No Safety option is open. Add a need-based or tuition-waiver route (Italian DSU, Finnish waivers, NL Scholarship).")
    else:
        recommendations.append(f"Safety anchor: {tiers['Safety'][0].scholarship.name}.")
    if len(tiers["Reach"]) > 3:
        recommendations.append("Many Reach options are open: pick at most 2 so each essay set gets enough time.")
    if tiers["Target"]:
        recommendations.append(f"Core: {len(tiers['Target'])} Target options, starting with {tiers['Target'][0].scholarship.name}.")
    passed = [m for m in matches if m.is_eligible and m.readiness and m.readiness.timeline_status == "Deadline passed"]
    if passed:
        recommendations.append("Closed for this intake (plan for next cycle): " + ", ".join(m.scholarship.name for m in passed[:5]) + ".")

    return {
        "candidate": profile.full_name,
        "normalized_gpa": round(profile.normalized_gpa, 2),
        "reach_opportunities": [item(m) for m in tiers["Reach"]],
        "target_opportunities": [item(m) for m in tiers["Target"]],
        "safety_opportunities": [item(m) for m in tiers["Safety"]],
        "recommended_portfolio": [item(m) for m in selected],
        "estimated_overall_success_probability": f"{success}%",
        "probability_note": "Rough heuristic from fixed base rates per tier and your fit score, not real admission statistics.",
        "portfolio_health": "Balanced" if tiers["Safety"] and tiers["Target"] else "Unbalanced (add Target/Safety options)",
        "strategic_recommendations": recommendations,
    }
