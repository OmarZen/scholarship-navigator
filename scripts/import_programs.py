#!/usr/bin/env python3
"""
Import program research (Erasmus Mundus masters, Intra-Africa projects) into data/programs/*.json.

Input: one or more JSON files, each a list of objects with these keys (unknown values may be null):
  acronym, name, type ("EMJM" | "Intra-Africa"), website, fields, field_groups, degree ("Master" or "Master, PhD"),
  duration_months, language, coordinator {university, country}, universities [{university, city, country}],
  host_countries, status (open | upcoming | self_funded_only | discontinued | unknown), scholarships_2027,
  deadline_2027_intake, latest_known_deadline, latest_known_cycle, deadline_notes, english_requirement,
  eligible_backgrounds, eligible_nationalities, source, confidence, notes

Usage:
  python scripts/import_programs.py research1.json [research2.json ...] [--intake 2027] [--verified 2026-10-25]

Existing records with the same id are replaced; others are kept. Run `cli.py validate --warnings` afterwards.
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from planner.models import Program  # noqa: E402
from planner.regions import normalize_country  # noqa: E402
from planner.fields import FIELD_GROUPS  # noqa: E402
from planner.language import to_ielts  # noqa: E402

OUT_DIR = REPO / "data" / "programs"
SCHEME_FILE = {"erasmus-mundus": "erasmus_mundus.json", "intra-africa-mobility": "intra_africa.json"}
DEGREES = ("Bachelor", "Master", "PhD", "Postdoc")


def slug(text: str) -> str:
    return "-".join(p for p in re.split(r"[^a-z0-9]+", text.lower()) if p)


def parse_ielts(text):
    if not text:
        return None
    m = re.search(r"IELTS[^0-9]{0,25}(\d(?:\.\d)?)", text, re.I)
    if m:
        return float(m.group(1))
    m = re.search(r"TOEFL[^0-9]{0,25}(\d{2,3})", text, re.I)
    if m:
        return to_ielts("TOEFL iBT", float(m.group(1)))
    return None


def deadline_block(rec, intake: int, verified: str):
    known = {}
    if rec.get("deadline_2027_intake"):
        known[str(intake)] = rec["deadline_2027_intake"]
    cycle = str(rec.get("latest_known_cycle") or "")
    m = re.match(r"(\d{4})", cycle)
    if rec.get("latest_known_deadline") and m:
        known.setdefault(m.group(1), rec["latest_known_deadline"])
    if not known:
        return None
    # Pattern from the most recent known date, expressed relative to its intake year.
    intake_year, iso = max(known.items())
    d = date.fromisoformat(iso)
    return {
        "month": d.month, "day": d.day, "years_before_intake": int(intake_year) - d.year,
        "precision": "exact" if str(intake) in known else "approx",
        "label": "Program application deadline (scholarship round)",
        "source": rec.get("source") or rec.get("website"), "verified_on": verified, "known_dates": known,
        "note": rec.get("deadline_notes"),
    }


def convert(rec, intake: int, verified: str) -> dict:
    kind = rec.get("type") or "EMJM"
    scheme = "intra-africa-mobility" if "africa" in kind.lower() else "erasmus-mundus"
    degrees = [d for d in DEGREES if d.lower() in str(rec.get("degree") or "Master").lower()] or ["Master"]
    universities = [
        {"university": u.get("university") or "?", "city": u.get("city"), "country": normalize_country(u.get("country") or "")}
        for u in rec.get("universities") or [] if u
    ]
    hosts = [normalize_country(c) for c in rec.get("host_countries") or [] if c]
    if not hosts:
        hosts = [u["country"] for u in universities if u["country"]]
    hosts = list(dict.fromkeys(hosts))
    coord = rec.get("coordinator") or None
    if coord:
        coord = {"university": coord.get("university") or "?", "city": coord.get("city"),
                 "country": normalize_country(coord.get("country") or "")}
    groups = [g for g in rec.get("field_groups") or [] if g in FIELD_GROUPS]
    nationality = {"mode": "include", "regions": ["africa"]} if scheme == "intra-africa-mobility" else {"mode": "any"}
    website = rec.get("website") or rec.get("source") or "https://www.eacea.ec.europa.eu/scholarships/erasmus-mundus-catalogue_en"
    status = rec.get("status") if rec.get("status") in ("open", "upcoming", "self_funded_only", "discontinued", "unknown") else "unknown"
    out = {
        "id": slug(rec["acronym"]),
        "acronym": rec["acronym"],
        "name": rec.get("name") or rec["acronym"],
        "type": "Intra-Africa" if scheme == "intra-africa-mobility" else "EMJM",
        "parent_scholarship": scheme,
        "website": website,
        "fields": rec.get("fields") or [],
        "field_groups": groups,
        "degrees": degrees,
        "duration_months": rec.get("duration_months"),
        "language": rec.get("language") or "English",
        "coordinator": coord,
        "universities": universities,
        "host_countries": hosts,
        "status": status,
        "scholarships_available": rec.get("scholarships_2027"),
        "deadline": deadline_block(rec, intake, verified),
        "deadline_notes": rec.get("deadline_notes"),
        "english_requirement": rec.get("english_requirement"),
        "ielts_min": parse_ielts(rec.get("english_requirement")),
        "eligible_backgrounds": rec.get("eligible_backgrounds"),
        "eligible_nationalities": rec.get("eligible_nationalities") or "Worldwide",
        "nationality": nationality,
        "source": rec.get("source"),
        "verified_on": verified,
        "confidence": rec.get("confidence") if rec.get("confidence") in ("high", "medium", "low") else None,
        "notes": rec.get("notes"),
    }
    Program(**out)  # validate
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--intake", type=int, default=2027)
    ap.add_argument("--verified", default=date.today().isoformat())
    args = ap.parse_args()

    incoming = {}
    for f in args.files:
        for rec in json.loads(Path(f).read_text(encoding="utf-8")):
            if not rec or not rec.get("acronym"):
                continue
            prog = convert(rec, args.intake, args.verified)
            incoming[prog["id"]] = prog  # later files win on duplicates

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    by_file = {}
    for prog in incoming.values():
        by_file.setdefault(SCHEME_FILE[prog["parent_scholarship"]], {})[prog["id"]] = prog
    for name, progs in by_file.items():
        path = OUT_DIR / name
        existing = {p["id"]: p for p in json.loads(path.read_text(encoding="utf-8"))} if path.exists() else {}
        existing.update(progs)
        ordered = sorted(existing.values(), key=lambda p: p["acronym"].lower())
        path.write_text(json.dumps(ordered, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"{path.relative_to(REPO)}: {len(progs)} imported, {len(ordered)} total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
