"""
Pydantic data models for candidate profiling, document inventory, scholarships,
eligibility rules, matching results, and roadmap generation.
"""

from datetime import date
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, model_validator

DegreeLevel = Literal["Bachelor", "Master", "PhD", "Postdoc"]
FundingPreference = Literal["Full", "Partial", "Any"]
MatchStatus = Literal["High Match", "Moderate Match", "Reach / Low Match", "Ineligible"]
EligibilityStatus = Literal["Eligible", "Needs Check", "Ineligible"]
CheckResult = Literal["pass", "fail", "unknown", "warn"]
DocStatus = Literal["have", "in_progress", "missing", "not_applicable"]
RequirementState = Literal["have", "partial", "in_progress", "expiring", "missing", "not_applicable"]
TimelineStatus = Literal[
    "On track", "Tight", "At risk", "Not feasible this cycle", "Deadline passed", "Deadline unknown", "Ready"
]
Tier = Literal["Reach", "Target", "Safety"]
ApplicationStatus = Literal[
    "Not Started", "Preparing Documents", "Drafting Essays", "Awaiting LORs", "Ready to Submit",
    "Submitted", "Interview Shortlisted", "Accepted / Awarded", "Rejected", "Skipped"
]
APPLICATION_STATUSES: List[str] = list(ApplicationStatus.__args__)  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Candidate
# ---------------------------------------------------------------------------

class LanguageSkill(BaseModel):
    language: str = Field(..., description="Language name, e.g. German, French, Spanish")
    level: Optional[str] = Field(default=None, description="CEFR level (A1-C2) or test score")
    certificate: Optional[str] = Field(default=None, description="Certificate name if any (Goethe B1, DELF B2...)")


class CandidateProfile(BaseModel):
    full_name: str = Field(..., description="Candidate's full name")
    nationality: str = Field(..., description="Candidate's country of citizenship")
    current_degree: str = Field(..., description="Current educational attainment (e.g. High School, Bachelor's, Master's)")
    target_degree: DegreeLevel = Field(..., description="Target degree level sought (Bachelor, Master, PhD, Postdoc)")
    field_of_study: str = Field(..., description="Field of study or prospective major (e.g., Computer Science, Economics)")
    gpa: float = Field(..., description="Grade point average (0.0 to 4.0 scale or converted)")
    gpa_scale: float = Field(default=4.0, description="Original GPA scale (e.g. 4.0, 5.0, 100%)")
    english_test: Optional[str] = Field(default=None, description="Test name if taken (IELTS, TOEFL, Duolingo, etc.)")
    english_score: Optional[float] = Field(default=None, description="Score on English exam")
    work_experience_years: float = Field(default=0.0, description="Full-time post-graduate professional work experience in years")
    research_publications: int = Field(default=0, description="Number of peer-reviewed publications or preprints")
    target_funding: FundingPreference = Field(default="Full", description="Target funding level: Full, Partial, or Any")
    target_countries: List[str] = Field(default_factory=list, description="Target countries or empty list for worldwide")
    target_intake_year: int = Field(default=2027, description="Target intake year (e.g., 2026, 2027)")
    budget_for_applications: str = Field(default="Moderate", description="Application fee budget: Zero, Moderate, Flexible")
    has_leadership_experience: bool = Field(default=True, description="Whether candidate has extracurricular/community leadership")

    # Personal details used by eligibility gates
    date_of_birth: Optional[date] = Field(default=None, description="Date of birth (YYYY-MM-DD) for age limits")
    country_of_residence: Optional[str] = Field(default=None, description="Where the candidate lives now (defaults to nationality)")
    email: Optional[str] = Field(default=None, description="Contact email used in drafts")
    phone: Optional[str] = Field(default=None, description="Contact phone used in drafts")

    # Education details
    university: Optional[str] = Field(default=None, description="University of the most recent degree")
    graduation_year: Optional[int] = Field(default=None, description="Year the most recent degree was (or will be) completed")
    class_rank_percent: Optional[float] = Field(default=None, description="Top X% of class, if known")
    thesis_title: Optional[str] = Field(default=None, description="Graduation project / thesis title")
    field_keywords: List[str] = Field(default_factory=list, description="Extra keywords describing the field (e.g. machine learning, embedded)")

    # Language details
    english_test_date: Optional[date] = Field(default=None, description="Date the English test was taken (results valid 2 years)")
    english_min_band: Optional[float] = Field(default=None, description="Lowest sub-score / band (IELTS scale or test's own scale)")
    other_languages: List[LanguageSkill] = Field(default_factory=list, description="Other languages and levels")

    # Experience & impact
    current_job_title: Optional[str] = Field(default=None, description="Current role")
    current_employer: Optional[str] = Field(default=None, description="Current employer")
    currently_employed: bool = Field(default=False, description="True if experience keeps accruing until the deadline")
    leadership_examples: List[str] = Field(default_factory=list, description="Short descriptions of leadership moments (STAR seeds)")
    awards: List[str] = Field(default_factory=list, description="Awards, honours, competitions")
    volunteering: List[str] = Field(default_factory=list, description="Volunteer and community work")
    publications: List[str] = Field(default_factory=list, description="Titles of publications / preprints")
    skills: List[str] = Field(default_factory=list, description="Technical and soft skills")

    # Goals & constraints
    career_goal: Optional[str] = Field(default=None, description="Post-study career goal in one or two sentences")
    home_country_problem: Optional[str] = Field(default=None, description="Problem at home the candidate wants to solve")
    willing_to_return_home: bool = Field(default=True, description="Accepts scholarships with a return-home obligation")
    has_dependents: bool = Field(default=False, description="Travelling with spouse/children")
    notes: Optional[str] = Field(default=None, description="Anything else an agent should know")

    @property
    def normalized_gpa(self) -> float:
        return (self.gpa / self.gpa_scale) * 4.0 if self.gpa_scale > 0 else self.gpa

    @property
    def residence(self) -> str:
        return self.country_of_residence or self.nationality

    def age_on(self, on: date) -> Optional[int]:
        if not self.date_of_birth:
            return None
        dob = self.date_of_birth
        return on.year - dob.year - ((on.month, on.day) < (dob.month, dob.day))


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

class CatalogDocument(BaseModel):
    id: str
    name: str
    category: str
    scope: Literal["shared", "per_scholarship"]
    lead_time_days: List[int] = Field(default_factory=lambda: [7, 21])
    validity_months: Optional[int] = None
    countable: bool = False
    satisfied_by: List[str] = Field(default_factory=list)
    how_to_obtain: str = ""
    tips: Optional[str] = None

    @property
    def lead_min(self) -> int:
        return self.lead_time_days[0]

    @property
    def lead_max(self) -> int:
        return self.lead_time_days[-1]


class DocumentRecord(BaseModel):
    """One paper the candidate holds (or is working on). Stored in profile/documents.json."""
    doc_id: str
    status: DocStatus = "missing"
    count_ready: int = Field(default=0, description="For countable papers (e.g. recommendation letters): how many are secured")
    files: List[str] = Field(default_factory=list, description="Paths relative to the workspace root")
    issued: Optional[date] = None
    expires: Optional[date] = None
    translated: Optional[bool] = None
    certified: Optional[bool] = None
    apostilled: Optional[bool] = None
    details: Optional[str] = None
    notes: Optional[str] = None

    @property
    def effective_count(self) -> int:
        if self.status != "have":
            return 0
        return max(1, self.count_ready)


class DocumentRequirement(BaseModel):
    """A paper a scholarship asks for, expressed against the document catalog."""
    doc: str
    label: str
    count: int = 1
    stage: Literal["application", "later"] = "application"
    optional: bool = False
    degrees: List[DegreeLevel] = Field(default_factory=list, description="Only for these target degrees (empty = all)")
    alternatives: List[str] = Field(default_factory=list, description="Catalog ids accepted instead")
    requires: List[str] = Field(default_factory=list, description="certified, translated, apostille, notarized, signed, template")
    words: Optional[int] = None
    items: List[str] = Field(default_factory=list, description="Essay prompts / topics, one per item")
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Scholarship
# ---------------------------------------------------------------------------

class CoverageDetails(BaseModel):
    tuition_covered: bool
    monthly_stipend: str
    airfare_covered: bool
    health_insurance: bool
    accommodation_covered: bool
    visa_fees_covered: bool
    additional_allowances: Optional[str] = None


class NationalityRule(BaseModel):
    mode: Literal["any", "include", "exclude", "verify"] = "any"
    countries: List[str] = Field(default_factory=list)
    regions: List[str] = Field(default_factory=list)
    exclude_countries: List[str] = Field(default_factory=list)
    exclude_regions: List[str] = Field(default_factory=list)
    note: Optional[str] = None
    source: Optional[str] = None
    verified_on: Optional[str] = None


class LanguageRule(BaseModel):
    required: bool = True
    ielts_min: Optional[float] = None
    subscore_min: Optional[float] = None
    accepts_moi: bool = False
    stage: Literal["application", "later"] = "application"
    other_language: Optional[str] = None
    other_language_level: Optional[str] = None
    note: Optional[str] = None


class FieldRule(BaseModel):
    mode: Literal["any", "priority", "restricted"] = "any"
    groups: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    note: Optional[str] = None


class EligibilityRules(BaseModel):
    nationality: NationalityRule = Field(default_factory=NationalityRule)
    residence: Optional[str] = Field(default=None, description="'home_country' or a region id such as 'africa'")
    residence_strict: bool = False
    gpa_min: Optional[float] = None
    gpa_competitive: Optional[float] = None
    language: LanguageRule = Field(default_factory=LanguageRule)
    age_min: Optional[int] = None
    age_under: Dict[str, int] = Field(default_factory=dict, description="Degree -> applicant must be younger than this")
    age_under_preferred: Dict[str, int] = Field(default_factory=dict, description="Soft (typical) age limits")
    degree_age_max_years: Optional[int] = None
    degree_age_strict: bool = True
    degree_age_applies_to: List[DegreeLevel] = Field(default_factory=list)
    work_experience_years: float = 0.0
    field: FieldRule = Field(default_factory=FieldRule)
    return_obligation_years: float = 0.0
    return_obligation_strict: bool = False
    leadership_weight: Literal["normal", "high"] = "normal"
    research_weight: Literal["normal", "high"] = "normal"


class ScholarshipEligibility(BaseModel):
    eligible_nationalities: str
    gpa_requirement: str
    language_requirements: str
    work_experience_years: float = 0.0
    work_hours_required: int = 0
    age_limit: Optional[str] = None
    field_restrictions: str
    return_obligation: Optional[str] = None
    rules: EligibilityRules = Field(default_factory=EligibilityRules)


class DeadlinePattern(BaseModel):
    month: int
    day: int
    years_before_intake: int = 0
    label: Optional[str] = None


class DeadlineEstimate(DeadlinePattern):
    precision: Literal["exact", "approx", "varies"] = "approx"
    source: Optional[str] = None
    verified_on: Optional[str] = None
    known_dates: Dict[str, str] = Field(default_factory=dict, description="Intake year -> published ISO date")
    extra: List[DeadlinePattern] = Field(default_factory=list, description="Other dates in the same cycle (priority rounds, second steps)")
    note: Optional[str] = None


class ScholarshipTimeline(BaseModel):
    opening_month: str
    typical_deadline: str
    interview_period: Optional[str] = None
    result_announcement: Optional[str] = None
    course_start: Optional[str] = None
    university_offer_deadline: Optional[str] = None
    sending_partner_nomination: Optional[str] = None
    deadline: Optional[DeadlineEstimate] = None


class Scholarship(BaseModel):
    id: str
    name: str
    country: str
    organization: str
    degrees: List[DegreeLevel]
    funding_type: FundingPreference
    coverage_details: CoverageDetails
    eligibility: ScholarshipEligibility
    timeline: ScholarshipTimeline
    documents: List[DocumentRequirement] = Field(default_factory=list)
    official_portal: str
    application_portal_system: str
    strategic_tips: str
    host_countries: List[str] = Field(default_factory=list)
    host_regions: List[str] = Field(default_factory=list)
    tier: Tier = "Target"
    program_status: Literal["active", "discontinued", "changed", "unknown"] = "active"
    program_status_note: Optional[str] = None
    data_last_reviewed: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _accept_legacy_documents(cls, data: Any) -> Any:
        # Older or scraped records only carry free-text `required_documents`.
        if isinstance(data, dict) and not data.get("documents") and data.get("required_documents"):
            data = dict(data)
            data["documents"] = [{"doc": "other", "label": label} for label in data["required_documents"]]
        return data

    @property
    def required_documents(self) -> List[str]:
        return [d.label for d in self.documents]

    @property
    def rules(self) -> EligibilityRules:
        return self.eligibility.rules


# ---------------------------------------------------------------------------
# Programs inside a scholarship scheme (e.g. one Erasmus Mundus Joint Master)
# ---------------------------------------------------------------------------

ProgramStatus = Literal["open", "upcoming", "self_funded_only", "discontinued", "unknown"]


class University(BaseModel):
    university: str
    city: Optional[str] = None
    country: str = ""


class Program(BaseModel):
    id: str
    acronym: str
    name: str
    type: str = Field(default="EMJM", description="EMJM (Erasmus Mundus Joint Master), Intra-Africa, ...")
    parent_scholarship: str = Field(default="erasmus-mundus", description="Scholarship id in data/scholarships.json")
    website: str
    fields: List[str] = Field(default_factory=list)
    field_groups: List[str] = Field(default_factory=list)
    degrees: List[DegreeLevel] = Field(default_factory=lambda: ["Master"])
    duration_months: Optional[int] = None
    language: Optional[str] = "English"
    coordinator: Optional[University] = None
    universities: List[University] = Field(default_factory=list)
    host_countries: List[str] = Field(default_factory=list)
    status: ProgramStatus = "unknown"
    scholarships_available: Optional[bool] = Field(default=None, description="Scholarships offered for the researched intake")
    deadline: Optional[DeadlineEstimate] = None
    deadline_notes: Optional[str] = None
    english_requirement: Optional[str] = None
    ielts_min: Optional[float] = None
    eligible_backgrounds: Optional[str] = None
    eligible_nationalities: str = "Worldwide"
    nationality: NationalityRule = Field(default_factory=NationalityRule)
    source: Optional[str] = None
    verified_on: Optional[str] = None
    confidence: Optional[Literal["high", "medium", "low"]] = None
    notes: Optional[str] = None


class ProgramMatch(BaseModel):
    program: Program
    score: float
    eligible: bool
    field_match: Literal["strong", "partial", "none"]
    matched_terms: List[str] = Field(default_factory=list)
    host_countries_in_targets: List[str] = Field(default_factory=list)
    deadline: Optional[date] = None
    deadline_is_estimate: bool = True
    days_left: Optional[int] = None
    open_for_intake: bool = True
    reasons: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Per-application state (scholarships/<id>/status.json)
# ---------------------------------------------------------------------------

class ApplicationState(BaseModel):
    scholarship_id: str
    application_status: str = "Not Started"
    deadline_confirmed: Optional[date] = None
    deadline_source: Optional[str] = None
    deadline_verified_on: Optional[date] = None
    documents: Dict[str, DocumentRecord] = Field(default_factory=dict)
    chosen_programs: List[str] = Field(default_factory=list)
    referees: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Matching output
# ---------------------------------------------------------------------------

class GateCheck(BaseModel):
    name: str
    result: CheckResult
    detail: str
    fix: Optional[str] = None


class ScoreComponent(BaseModel):
    key: str
    name: str
    weight: float
    points: float
    detail: str


class RequirementStatus(BaseModel):
    doc: str
    name: str
    label: str
    scope: str
    category: str
    stage: str
    optional: bool
    count: int
    count_ready: int
    state: RequirementState
    units: float = Field(..., description="0..1 readiness contribution")
    lead_time_days: List[int]
    start_by: Optional[date] = None
    issues: List[str] = Field(default_factory=list)
    how_to_obtain: str = ""
    requires: List[str] = Field(default_factory=list)
    words: Optional[int] = None
    items: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    satisfied_via: Optional[str] = None


class ReadinessReport(BaseModel):
    percent: float
    requirements: List[RequirementStatus] = Field(default_factory=list)
    deadline: Optional[date] = None
    deadline_is_estimate: bool = True
    deadline_precision: str = "approx"
    deadline_label: str = "Not set"
    deadline_source: Optional[str] = None
    next_cycle_deadline: Optional[date] = None
    days_left: Optional[int] = None
    timeline_status: TimelineStatus = "Deadline unknown"
    longest_missing_lead_days: int = 0

    @property
    def missing(self) -> List[RequirementStatus]:
        return [r for r in self.requirements if r.stage == "application" and not r.optional and r.units < 1.0]

    @property
    def have_count(self) -> int:
        return sum(1 for r in self.requirements if r.stage == "application" and not r.optional and r.units >= 1.0)

    @property
    def total_count(self) -> int:
        return sum(1 for r in self.requirements if r.stage == "application" and not r.optional)


class MatchResult(BaseModel):
    scholarship: Scholarship
    match_score: float = Field(..., description="Fit score shown to the user (0 when ineligible)")
    match_status: MatchStatus
    fit_score: float = 0.0
    eligibility_status: EligibilityStatus = "Eligible"
    gate_checks: List[GateCheck] = Field(default_factory=list)
    score_breakdown: List[ScoreComponent] = Field(default_factory=list)
    readiness: Optional[ReadinessReport] = None
    priority_score: float = 0.0
    tier: Tier = "Target"
    reasons_eligible: List[str] = Field(default_factory=list)
    gaps_and_warnings: List[str] = Field(default_factory=list)
    strategic_recommendations: List[str] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)

    @property
    def is_eligible(self) -> bool:
        return self.eligibility_status != "Ineligible"

    @property
    def readiness_percent(self) -> float:
        return self.readiness.percent if self.readiness else 0.0
