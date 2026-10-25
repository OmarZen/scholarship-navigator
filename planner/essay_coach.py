"""
AI Essay & STAR Method Reviewer / Admissions Coach.
Evaluates scholarship essays (Chevening, Fulbright, Master SOPs) against
word count boundaries, STAR technique implementation, clichés, and impact metrics.
"""

import re
from typing import Dict, Any, List, Literal

EssayType = Literal[
    "chevening_leadership",
    "chevening_networking",
    "chevening_study_uk",
    "chevening_career",
    "fulbright_personal",
    "fulbright_study",
    "sop"
]

CLICHES = [
    "ever since i was a child",
    "from an early age",
    "as long as i can remember",
    "i have always been passionate",
    "i have always dreamed of",
    "i am a hard worker",
    "it has always been my dream",
    "since my childhood",
    "my passion started when",
    "in today's globalized world",
    "to whom it may concern"
]

ACTION_VERBS = [
    "spearheaded", "orchestrated", "negotiated", "formulated", "implemented",
    "mobilized", "revamped", "pioneered", "engineered", "streamlined",
    "co-founded", "developed", "executed", "delegated", "mentored",
    "analyzed", "transformed", "designed", "optimized", "managed"
]

METRIC_INDICATORS = [
    r"[0-9]+%", r"\$[0-9]+", r"£[0-9]+", r"€[0-9]+", r"[0-9]+\s+(?:people|students|users|clients|participants|members|engineers|patients)",
    r"increased by", r"reduced by", r"decreased by", r"saved", r"generated"
]


def review_scholarship_essay(text: str, essay_type: EssayType = "chevening_leadership") -> Dict[str, Any]:
    text_clean = text.strip()
    words = text_clean.split()
    word_count = len(words)
    text_lower = text_clean.lower()

    score = 100.0
    strengths: List[str] = []
    gaps: List[str] = []
    suggestions: List[str] = []
    found_cliches: List[str] = []

    # 1. Word Count Auditing
    limits = {
        "chevening_leadership": (400, 500),
        "chevening_networking": (400, 500),
        "chevening_study_uk": (400, 500),
        "chevening_career": (400, 500),
        "fulbright_personal": (500, 750),
        "fulbright_study": (600, 900),
        "sop": (700, 1100)
    }

    min_words, max_words = limits.get(essay_type, (400, 600))
    if word_count < min_words:
        score -= 20.0
        gaps.append(f"Word count deficit: Current length is {word_count} words (recommended minimum: {min_words} words). Essay lacks sufficient depth.")
        suggestions.append(f"Expand on specific obstacles faced and quantify the tangible outcomes achieved.")
    elif word_count > max_words:
        score -= 15.0
        gaps.append(f"Word count exceeded: Current length is {word_count} words (maximum allowed: {max_words} words). Will be automatically truncated by portal.")
        suggestions.append(f"Trim {word_count - max_words} words. Remove redundant adjectives and filler introductory sentences.")
    else:
        strengths.append(f"Optimal length: {word_count} words (within the ideal {min_words}-{max_words} target window).")

    # 2. Cliché Detection
    for c in CLICHES:
        if c in text_lower:
            found_cliches.append(c)
            score -= 8.0

    if found_cliches:
        quoted = ", ".join('"' + c + '"' for c in found_cliches)
        gaps.append(f"Detected amateur clichés: {quoted}.")
        suggestions.append("Replace clichés with immediate, concrete real-world problem statements or intellectual catalysts.")
    else:
        strengths.append("No common admissions clichés detected. Tone is mature and professional.")

    # 3. Action Verbs & Leadership Vocabulary
    verbs_used = [v for v in ACTION_VERBS if re.search(rf"\b{v}\b", text_lower)]
    if len(verbs_used) >= 4:
        strengths.append(f"Strong active voice: Uses commanding action verbs ({', '.join(verbs_used[:4])}).")
    elif len(verbs_used) >= 2:
        strengths.append(f"Moderate active voice: Uses action verbs ({', '.join(verbs_used)}).")
    else:
        score -= 12.0
        gaps.append("Passive voice predominance: Lacks strong leadership and execution verbs.")
        suggestions.append(f"Incorporate high-impact action verbs (e.g. spearheaded, orchestrated, negotiated, streamlined).")

    # 4. Quantifiable Metrics & Evidence
    metric_matches = []
    for pat in METRIC_INDICATORS:
        found = re.findall(pat, text_clean, re.IGNORECASE)
        metric_matches.extend(found)

    if len(metric_matches) >= 3:
        strengths.append(f"Highly quantifiable results: Contains {len(metric_matches)} concrete metrics/percentages/counts.")
    elif len(metric_matches) >= 1:
        strengths.append(f"Quantifiable elements present: Cites metrics ({', '.join(metric_matches[:2])}).")
    else:
        score -= 15.0
        gaps.append("Unsubstantiated claims: Lacks quantifiable metrics, statistics, percentages, or participant numbers.")
        suggestions.append("Quantify your achievements: How many people attended? What percentage was performance improved? How much budget was saved?")

    # 5. Type-Specific Assessments
    if essay_type == "chevening_leadership":
        # Check STAR components
        has_situation = any(w in text_lower for w in ["challenge", "problem", "obstacle", "crisis", "struggled", "faced"])
        has_task = any(w in text_lower for w in ["task", "responsibility", "assigned", "objective", "role was", "appointed"])
        has_action = any(w in text_lower for w in ["i decided", "i organized", "i took", "i spearheaded", "i led", "i formulated", "my approach"])
        has_result = any(w in text_lower for w in ["result", "achieved", "successfully", "impact", "outcome", "awarded", "resolved"])

        star_count = sum([has_situation, has_task, has_action, has_result])
        if star_count == 4:
            strengths.append("Full STAR Method Implementation: Situation, Task, Action, and Result are explicitly identifiable.")
        else:
            missing = []
            if not has_situation: missing.append("Situation (Clear context/problem)")
            if not has_task: missing.append("Task (Your explicit responsibility)")
            if not has_action: missing.append("Action (Concrete steps YOU took, using 'I' not 'We')")
            if not has_result: missing.append("Result (Measurable positive outcome)")
            score -= (4 - star_count) * 8.0
            gaps.append(f"Incomplete STAR structure: Missing {', '.join(missing)}.")
            suggestions.append("Structure your core story chronologically: 1) What was the crisis? 2) What was your role? 3) What did YOU do? 4) What was the measurable outcome?")

    elif essay_type == "chevening_study_uk":
        has_three_courses = len(re.findall(r"(?:university|msc|master|course|choice)", text_lower)) >= 3
        if not has_three_courses:
            score -= 15.0
            gaps.append("UK Course Alignment: Must clearly outline your 3 chosen master's courses and universities.")
            suggestions.append("Name the 3 UK universities and explain how the modules logically interconnect.")

    score = max(10.0, min(100.0, score))
    readiness = "Admissions Ready (Elite Tier)" if score >= 85 else ("Competitive (Needs Minor Polish)" if score >= 70 else "Revision Required")

    return {
        "essay_type": essay_type,
        "word_count": word_count,
        "readiness_score": round(score, 1),
        "readiness_level": readiness,
        "strengths": strengths,
        "gaps_and_flags": gaps,
        "actionable_suggestions": suggestions
    }
