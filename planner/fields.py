"""
Field-of-study taxonomy: maps free-text fields ("Embedded Systems and AI") to broad groups
so they can be compared with a scholarship's priority or restricted fields.
"""

import re
from typing import Iterable, List, Set

FIELD_GROUPS = {
    "computing": [
        "computer science", "computing", "informatics", "ict", "information technology", "information systems",
        "software", "data science", "artificial intelligence", "ai", "machine learning", "deep learning",
        "computer vision", "natural language processing", "nlp", "robotics", "digital", "cyber", "embedded",
        "computer engineering", "electrical and computer", "data", "computational",
    ],
    "engineering": [
        "engineering", "electrical", "electronics", "electronic", "mechanical", "civil", "chemical engineering",
        "technical sciences", "embedded", "robotics", "energy", "energetics", "renewable", "telecommunication",
        "mechatronics", "aerospace", "industrial", "materials", "biomedical engineering", "infrastructure",
    ],
    "natural_sciences": [
        "physics", "chemistry", "biology", "mathematics", "math", "statistics", "exact sciences", "natural sciences",
        "marine", "physical sciences", "geology", "earth sciences", "biotechnology", "life sciences", "biological",
    ],
    "health": [
        "medicine", "medical", "public health", "health", "nursing", "pharmacy", "biomedical", "global health",
        "epidemiology", "dentistry", "nutrition",
    ],
    "agriculture": [
        "agriculture", "agricultural", "food security", "food", "water resources", "forestry", "veterinary",
        "agronomy", "fisheries", "aquaculture", "rural development",
    ],
    "environment": [
        "environment", "environmental", "climate", "sustainability", "sustainable", "ecological", "ecology",
        "water", "renewable energy", "disaster", "conservation", "energy transition",
    ],
    "economics_business": [
        "economics", "economic", "business", "management", "finance", "accounting", "mba",
        "business administration", "entrepreneurship", "marketing", "supply chain",
    ],
    "social_sciences": [
        "social sciences", "sociology", "political science", "politics", "international relations", "public policy",
        "governance", "public administration", "law", "peace", "conflict", "development studies", "development",
        "media", "journalism", "education", "regional planning", "urban planning", "psychology", "gender",
        "human rights", "anthropology",
    ],
    "humanities": [
        "humanities", "history", "philosophy", "languages", "literature", "arts", "linguistics", "archaeology",
        "music", "design", "architecture", "theology", "cultural",
    ],
}


def _contains_term(text: str, term: str) -> bool:
    return re.search(r"(?<![a-z])" + re.escape(term) + r"(?![a-z])", text) is not None


def groups_for(texts: Iterable[str]) -> Set[str]:
    blob = " ".join(t.lower() for t in texts if t)
    return {g for g, terms in FIELD_GROUPS.items() if any(_contains_term(blob, t) for t in terms)}


def keyword_hits(texts: Iterable[str], keywords: List[str]) -> List[str]:
    blob = " ".join(t.lower() for t in texts if t)
    return [k for k in keywords if _contains_term(blob, k.lower())]
