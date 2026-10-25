"""
PhD & Research Master's Supervisor Outreach (Cold Email) Generator.
Generates tailored, high-conversion emails for securing laboratory acceptance letters
for MEXT, CSC Type B, Swiss Excellence, DAAD PhD, KAUST, and US/Canadian RA/TA positions.
"""

from typing import Dict, Any, Optional
from .models import CandidateProfile


def generate_supervisor_email(
    profile: CandidateProfile,
    professor_name: str,
    university_name: str,
    laboratory_or_field: str,
    relevant_paper_or_topic: Optional[str] = None,
    scholarship_target: str = "Swiss Government Excellence / Full Fellowship"
) -> Dict[str, str]:
    prof_salutation = f"Professor {professor_name.split()[-1]}" if "prof" not in professor_name.lower() else professor_name
    normalized_gpa = (profile.gpa / profile.gpa_scale) * 4.0

    subject = f"Prospective {profile.target_degree} Researcher: Inquiry regarding {laboratory_or_field} ({profile.full_name})"

    paper_mention = ""
    if relevant_paper_or_topic:
        paper_mention = (
            f"I have been following your laboratory's work with great admiration, particularly your recent research "
            f"on '{relevant_paper_or_topic}'. The methodological approach you demonstrated in that work directly resonates "
            f"with my ongoing investigations."
        )
    else:
        paper_mention = (
            f"I have been closely reading your laboratory's publications in {laboratory_or_field}. Your team's "
            f"innovative contributions in this domain closely parallel my research interests."
        )

    pub_mention = ""
    if profile.research_publications > 0:
        pub_mention = (
            f"During my previous academic career, I co-authored {profile.research_publications} peer-reviewed research contribution(s) "
            f"focusing on {profile.field_of_study}."
        )
    else:
        pub_mention = (
            f"During my {profile.current_degree}, I completed a thesis focusing on {profile.field_of_study}, "
            f"achieving a cumulative GPA of {normalized_gpa:.2f}/4.0."
        )

    body = f"""Dear {prof_salutation},

I hope this email finds you well.

My name is {profile.full_name}, and I am writing to express my strong enthusiasm for pursuing a {profile.target_degree} degree under your supervision at {university_name}, starting in {profile.target_intake_year}.

{paper_mention}

{pub_mention} In particular, I have developed solid foundational skills in research design, data analysis, and technical problem-solving relevant to {laboratory_or_field}.

I am preparing my application for the prestigious {scholarship_target}, which provides comprehensive full funding (covering full tuition, health insurance, international travel, and a competitive monthly living stipend). Therefore, my appointment would require zero financial strain on your departmental research grants.

I have attached my academic CV, transcripts, and a concise 2-page Research Concept Note for your perusal. 

If my profile aligns with your current laboratory goals, would you be open to a brief 15-minute video conversation in the coming weeks to discuss potential mutual fit?

Thank you very much for your time and consideration.

Sincerely,

{profile.full_name}
{profile.nationality}
Email: [Your Professional Email]
LinkedIn / Google Scholar: [Your Profile Link]
"""

    return {
        "recipient": f"{professor_name} ({university_name})",
        "subject": subject,
        "body": body.strip(),
        "attachments_checklist": "1) Academic CV (Europass / 2-page Standard), 2) Complete Grade Transcripts, 3) 2-page Research Concept Note"
    }
