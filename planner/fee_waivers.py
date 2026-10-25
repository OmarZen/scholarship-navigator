"""
Application Fee Waiver Navigator & Hardship Request Generator.
Provides lists of zero-cost application portals and generates professional fee waiver request emails.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from .models import CandidateProfile


def load_fee_waiver_data() -> List[Dict[str, Any]]:
    path = Path(__file__).parent.parent / "data" / "fee_waivers.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_fee_waiver_email(
    profile: CandidateProfile,
    university_name: str,
    program_name: str,
    department_chair_or_admissions: str = "Graduate Admissions Committee"
) -> Dict[str, str]:
    normalized_gpa = (profile.gpa / profile.gpa_scale) * 4.0

    subject = f"Application Fee Waiver Request - {program_name} ({profile.full_name})"

    body = f"""Dear {department_chair_or_admissions},

I hope this email finds you well.

My name is {profile.full_name}, an aspiring postgraduate scholar from {profile.nationality}. I am writing to respectfully request consideration for an application fee waiver for the {program_name} program at {university_name} for the {profile.target_intake_year} intake.

I have maintained an exceptional academic record, completing my {profile.current_degree} with a cumulative GPA of {normalized_gpa:.2f}/4.0. My research interests in {profile.field_of_study} closely align with your department's pioneering research initiatives.

Due to severe local currency devaluation and economic constraints in my home country, the required international application fee constitutes a substantial financial burden that hinders my ability to submit my application without extreme personal hardship.

Receiving a fee waiver would enable me to present my qualifications for admission and subsequent institutional scholarship consideration. I have prepared all other academic documents, transcripts, and letters of recommendation for immediate submission upon your approval.

Thank you very much for your time, empathy, and consideration of my request.

Sincerely,

{profile.full_name}
{profile.nationality}
Email: [Your Professional Email]
Attached: CV & Unofficial Academic Transcripts
"""

    return {
        "subject": subject,
        "body": body.strip(),
        "advice": "Send this email 3 to 4 weeks before the application deadline directly to the graduate admissions coordinator or department chair."
    }

