"""
English test score conversion to an IELTS-band equivalent (rounded official concordance tables).
"""

from typing import Optional

# Approximate concordance tables -> IELTS band equivalent (official concordances, rounded).
TOEFL_TO_IELTS = [(118, 9.0), (115, 8.5), (110, 8.0), (102, 7.5), (94, 7.0), (79, 6.5), (60, 6.0), (46, 5.5), (35, 5.0), (32, 4.5)]
DUOLINGO_TO_IELTS = [(155, 8.5), (150, 8.0), (140, 7.5), (130, 7.0), (120, 6.5), (110, 6.0), (100, 5.5), (90, 5.0)]
PTE_TO_IELTS = [(89, 9.0), (84, 8.5), (79, 8.0), (73, 7.5), (66, 7.0), (59, 6.5), (51, 6.0), (43, 5.5), (36, 5.0)]
CAMBRIDGE_TO_IELTS = [(209, 9.0), (205, 8.5), (200, 8.0), (191, 7.5), (185, 7.0), (176, 6.5), (169, 6.0), (162, 5.5)]



def to_ielts(test: Optional[str], score: Optional[float]) -> Optional[float]:
    if score is None or not test:
        return None
    t = test.lower()
    table = None
    if "ielts" in t:
        return float(score)
    if "toefl" in t:
        table = TOEFL_TO_IELTS
    elif "duolingo" in t or t.strip() == "det":
        table = DUOLINGO_TO_IELTS
    elif "pte" in t:
        table = PTE_TO_IELTS
    elif "cambridge" in t or "cae" in t or "cpe" in t or "c1 advanced" in t:
        table = CAMBRIDGE_TO_IELTS
    if not table:
        return None
    for threshold, band in table:
        if score >= threshold:
            return band
    return 4.0
