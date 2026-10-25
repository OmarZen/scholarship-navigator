"""
Multi-Perspective Letter of Recommendation (LOR) & Recommender Brag Sheet Generator.
Generates authentic, high-impact reference letters and a 1-page brag sheet to give to professors/employers.
"""

from typing import Dict, Any, Literal
from .models import CandidateProfile

LORPerspective = Literal["academic_supervisor", "academic_instructor", "professional_employer"]


def generate_recommendation_letter(
    profile: CandidateProfile,
    recommender_name: str,
    recommender_title: str,
    institution_or_company: str,
    perspective: LORPerspective = "academic_supervisor",
    relationship_years: float = 2.0,
    scholarship_target: str = "Chevening / Global Excellence Scholarship"
) -> Dict[str, str]:
    normalized_gpa = (profile.gpa / profile.gpa_scale) * 4.0

    if perspective == "academic_supervisor":
        subject = f"Confidential Letter of Recommendation for {profile.full_name} ({profile.target_degree} Candidate)"
        body = f"""Dear Members of the Scholarship Selection Committee,

It is my distinct privilege to write this letter of highest recommendation for {profile.full_name}, who is applying for the prestigious {scholarship_target}. I serve as {recommender_title} at {institution_or_company}, and I have known {profile.full_name} for the past {relationship_years:.1f} years, during which I had the pleasure of supervising their capstone research and thesis work in {profile.field_of_study}.

Among the hundreds of students I have taught and mentored over my career, {profile.full_name} ranks comfortably within the top 5% in terms of intellectual maturity, analytical perseverance, and methodological rigor. During their thesis project, {profile.full_name} demonstrated an exceptional ability to independently formulate research hypotheses, review technical literature, and execute complex empirical analyses with precision.

What distinguishes {profile.full_name} is not merely their strong academic record (cumulative GPA of {normalized_gpa:.2f}/4.0), but their relentless intellectual curiosity and resilience when confronting research bottlenecks. When faced with ambiguous experimental challenges, {profile.full_name} approached the problem with disciplined scientific inquiry, exploring novel techniques rather than settling for conventional solutions.

Beyond individual scholarship, {profile.full_name} exhibited exemplary teamwork, often mentoring junior peers in our laboratory and presenting complex technical concepts with remarkable clarity.

I have zero hesitation in confirming that {profile.full_name} possesses the academic horsepower, ethical integrity, and research dedication required to excel in demanding {profile.target_degree} studies abroad and emerge as an impactful leader in their field upon graduation. I recommend them with my highest enthusiasm.

Sincerely,

{recommender_name}
{recommender_title}
{institution_or_company}
Email: [Official University Email]
Phone: [Official University Phone]
"""

    elif perspective == "academic_instructor":
        subject = f"Academic Reference for {profile.full_name} ({profile.target_degree} Program)"
        body = f"""To the Scholarship Admissions Committee,

I am writing this reference letter in enthusiastic support of {profile.full_name}'s application for the {scholarship_target}. As {recommender_title} in the Department of {profile.field_of_study} at {institution_or_company}, I instructed {profile.full_name} across multiple advanced university courses over the past {relationship_years:.1f} years.

Throughout our coursework, {profile.full_name} stood out as an engaged, intellectually fearless participant who consistently elevated classroom discussions. They demonstrated a sophisticated grasp of core theoretical foundations and possessed a rare capacity to translate abstract concepts into tangible engineering and analytical solutions. In group projects, {profile.full_name} naturally emerged as a consensus builder, ensuring high-quality project deliverables while encouraging peer collaboration.

Their academic track record ({normalized_gpa:.2f}/4.0 GPA) speaks to their consistency and diligence. More importantly, {profile.full_name} approaches learning with genuine humility and an insatiable desire to solve practical, real-world problems.

I am confident that {profile.full_name} will thrive in an international academic environment and make meaningful contributions to your scholarly community. They have my full, unreserved endorsement.

Warm regards,

{recommender_name}
{recommender_title}
{institution_or_company}
"""

    else: # professional_employer
        subject = f"Professional Recommendation & Leadership Endorsement: {profile.full_name}"
        body = f"""Dear Selection Board,

I am writing to express my strongest endorsement of {profile.full_name} for the {scholarship_target}. As {recommender_title} at {institution_or_company}, I have had the privilege of directly managing and collaborating with {profile.full_name} for the past {relationship_years:.1f} years.

In our organization, {profile.full_name} has proven to be an indispensable asset, distinguished by their strategic execution, proactive initiative, and calm leadership under tight operational deadlines. They have consistently taken ownership of complex projects, successfully coordinating cross-functional stakeholders and delivering measurable results that enhanced our team's performance.

What sets {profile.full_name} apart as an international scholarship candidate is their deep sense of purpose and commitment to community transformation. In every project, they demonstrate not just technical competence, but high emotional intelligence, professional ethics, and an innate drive to implement sustainable improvements.

We fully support their pursuit of advanced {profile.target_degree} education through the {scholarship_target}. We are convinced that the specialized global knowledge and international network they acquire will empower them to drive transformative change upon returning to our home country's industry. I give {profile.full_name} my highest professional recommendation.

Sincerely,

{recommender_name}
{recommender_title}
{institution_or_company}
Email: [Official Corporate Email]
"""

    return {
        "perspective": perspective,
        "subject": subject,
        "body": body.strip(),
        "advice": "Ensure the referee prints this letter on official institutional letterhead with official corporate/university email, physical ink signature, and official department/organization stamp."
    }


def generate_recommender_brag_sheet(profile: CandidateProfile, target_scholarships: list) -> str:
    normalized_gpa = (profile.gpa / profile.gpa_scale) * 4.0
    s_names = ", ".join(target_scholarships[:4]) if target_scholarships else "International Postgraduate Scholarships"

    brag_sheet = f"""================================================================================
CANDIDATE BRAG SHEET FOR RECOMMENDERS (CONFIDENTIAL SUMMARY)
================================================================================
Applicant: {profile.full_name}
Target Degree: {profile.target_degree} in {profile.field_of_study}
Target Intake: {profile.target_intake_year}
Target Scholarships: {s_names}

1. ACADEMIC HIGHLIGHTS:
   • Undergraduate Degree: {profile.current_degree}
   • Cumulative Normalized GPA: {normalized_gpa:.2f} / 4.0 (Top echelon of cohort)
   • Academic Publications / Theses: {profile.research_publications} contribution(s)
   • Language Proficiency: {profile.english_test or 'Certified'} ({profile.english_score or 'Verified'})

2. RELEVANT PRACTICAL & WORK ACHIEVEMENTS:
   • Total Professional Experience: {profile.work_experience_years:.1f} Years
   • Leadership Experience: Active community & project leadership

3. PROPOSED POSTGRADUATE STUDY VISION:
   • Why this study abroad: To master advanced methodologies and technologies in {profile.field_of_study}
   • Post-graduation plan: Return to home country to apply acquired expertise in national development projects

4. INSTRUCTIONS FOR THE REFEREE:
   • Please mention how long and in what capacity you have known the applicant.
   • Specific examples of problem-solving, intellectual curiosity, or team leadership are far more impactful than generic praise.
   • Please print on official letterhead, sign physically, and stamp if possible.
================================================================================
"""
    return brag_sheet

