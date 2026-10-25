#!/usr/bin/env python3
"""
MCP server for the Global Scholarship Navigator.

Lets any MCP client (Claude Code, Claude Desktop, Cursor, Windsurf, ...) match candidates to scholarships,
find Erasmus Mundus / Intra-Africa programs, and manage a candidate workspace.

Run:   .venv/bin/python mcp_server.py            (stdio transport)
Config example: see .mcp.json and README.md ("Use with AI agents").
Workspaces are stored in $SCHOLARSHIP_WORKSPACES (default: <repo>/output).
"""

from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from planner import api

INSTRUCTIONS = """Scholarship Navigator: eligibility, fit scores, missing papers and dated plans for 35 major scholarships
plus individual Erasmus Mundus / Intra-Africa programs.

Typical flow:
1. Interview the candidate (nationality, residence, date of birth, degree, GPA + scale, graduation year, English test +
   date, work years, field + keywords, leadership stories, target degree/countries/intake, papers they already hold).
2. create_workspace(profile) -> saves everything under output/<name>/ and returns shortlist, next actions, missing papers.
3. Explain results: eligibility first, then fit (0-100) and readiness (% of papers held). Deadlines marked estimated
   must be verified on the official site, then recorded with confirm_deadline.
4. Keep it current with update_document, set_application_status, choose_program.
Never invent grades, achievements or eligibility. Answer in the candidate's language."""

mcp = FastMCP("scholarship-navigator", instructions=INSTRUCTIONS)


@mcp.tool()
def list_scholarships(degree: Optional[str] = None, country: Optional[str] = None,
                      funding: Optional[str] = None) -> List[Dict[str, Any]]:
    """List scholarships in the database. Filters: degree (Bachelor|Master|PhD|Postdoc), country text, funding (Full|Partial)."""
    return api.list_scholarships(degree, country, funding)


@mcp.tool()
def get_scholarship(scholarship_id: str) -> Dict[str, Any]:
    """Full record for one scholarship: coverage, published eligibility, structured rules, required papers, deadlines."""
    return api.get_scholarship(scholarship_id)


@mcp.tool()
def match_scholarships(profile: Dict[str, Any], include_ineligible: bool = False, limit: int = 15) -> Dict[str, Any]:
    """Score a candidate against every scholarship without creating files.

    profile: CandidateProfile fields (full_name, nationality, current_degree, target_degree, field_of_study, gpa,
    gpa_scale, english_test, english_score, work_experience_years, target_countries, target_intake_year,
    date_of_birth, graduation_year, ...) plus optional "documents": [{"doc_id": "passport", "status": "have"}, ...].
    Returns ranked results with eligibility checks, fit breakdown, readiness, missing papers and a dated plan."""
    return api.match(profile, include_ineligible=include_ineligible, limit=limit)


@mcp.tool()
def find_programs(profile: Optional[Dict[str, Any]] = None, field: Optional[str] = None,
                  countries: Optional[List[str]] = None, scheme: Optional[str] = None,
                  limit: int = 20, include_closed: bool = False) -> List[Dict[str, Any]]:
    """Find individual programs (Erasmus Mundus Joint Masters, Intra-Africa projects) with host countries,
    universities, status and deadlines. Give a profile to rank by fit, or just a field (e.g. "robotics") and/or
    host countries. scheme: "erasmus-mundus" or "intra-africa-mobility"."""
    return api.find_programs(profile, field, countries, scheme, limit, include_closed)


@mcp.tool()
def list_document_types() -> List[Dict[str, Any]]:
    """Every paper type (passport, transcript, lor_academic, motivation_letter, ...) with lead time and how to get it."""
    return api.list_document_types()


@mcp.tool()
def create_workspace(profile: Dict[str, Any], name: Optional[str] = None, overwrite_profile: bool = False) -> Dict[str, Any]:
    """Create (or refresh) the candidate's workspace folder with briefs, drafts, Excel, HTML and calendar.
    Returns the folder path, shortlist, next actions, missing papers and recommended programs."""
    return api.create_workspace(profile, name, overwrite_profile)


@mcp.tool()
def workspace_summary(workspace: Optional[str] = None) -> Dict[str, Any]:
    """Rebuild and summarise a workspace (folder name under output/, or a path). Omit when only one exists."""
    return api.workspace_summary(workspace)


@mcp.tool()
def scholarship_brief(scholarship_id: str, workspace: Optional[str] = None) -> str:
    """Markdown brief for one shortlisted scholarship: checks, score breakdown, papers, timeline, programs."""
    return api.scholarship_brief(scholarship_id, workspace)


@mcp.tool()
def update_document(doc_id: str, status: Optional[str] = None, workspace: Optional[str] = None,
                    scholarship_id: Optional[str] = None, file: Optional[str] = None, issued: Optional[str] = None,
                    expires: Optional[str] = None, count: Optional[int] = None, translated: Optional[bool] = None,
                    certified: Optional[bool] = None, apostilled: Optional[bool] = None,
                    details: Optional[str] = None) -> Dict[str, Any]:
    """Record a paper the candidate holds. status: have | in_progress | missing | not_applicable.
    Use scholarship_id for per-application papers (essay, motivation_letter, application_form...).
    count = recommendation letters secured. Dates are YYYY-MM-DD. Rebuilds the workspace."""
    return api.update_document(doc_id, status, workspace, scholarship_id, file, issued, expires, count,
                               translated, certified, apostilled, details)


@mcp.tool()
def confirm_deadline(scholarship_id: str, deadline: str, source: Optional[str] = None,
                     workspace: Optional[str] = None) -> Dict[str, Any]:
    """Record a deadline verified on the official site (YYYY-MM-DD) with its source URL."""
    return api.confirm_deadline(scholarship_id, deadline, source, workspace)


@mcp.tool()
def set_application_status(scholarship_id: str, status: str, workspace: Optional[str] = None,
                           notes: Optional[str] = None) -> Dict[str, Any]:
    """Track an application: Not Started, Preparing Documents, Drafting Essays, Awaiting LORs, Ready to Submit,
    Submitted, Interview Shortlisted, Accepted / Awarded, Rejected, Skipped. Tracking a non-shortlisted
    scholarship gives it a folder; Skipped removes it from the shortlist."""
    return api.set_application_status(scholarship_id, status, workspace, notes)


@mcp.tool()
def choose_program(program_id: str, workspace: Optional[str] = None, remove: bool = False) -> Dict[str, Any]:
    """Choose (or un-choose) a program, e.g. one of up to 3 Erasmus Mundus masters. Creates a tailored
    motivation-letter draft and makes the scheme's deadline follow the chosen programs."""
    return api.choose_program(program_id, workspace, remove)


@mcp.tool()
def country_guide(country: str) -> Dict[str, Any]:
    """Study/work rules, living costs, post-study visa, visa dossier, housing and credential recognition for a country."""
    return api.country_guide(country)


@mcp.tool()
def funding_gap(country: str, monthly_stipend: float = 0.0, months: int = 12, covers_tuition: bool = True,
                covers_flights: bool = False, covers_insurance: bool = False,
                private_university: bool = False) -> Dict[str, Any]:
    """Cost of attendance, out-of-pocket deficit and visa proof-of-funds (e.g. German blocked account)."""
    return api.funding_gap(country, monthly_stipend, months, covers_tuition, covers_flights, covers_insurance,
                           private_university)


@mcp.tool()
def review_essay(text: str, essay_type: str = "sop") -> Dict[str, Any]:
    """Review an essay (STAR structure, metrics, cliches, word count). essay_type: chevening_leadership,
    chevening_networking, chevening_study_uk, chevening_career, fulbright_personal, fulbright_study, sop."""
    return api.review_essay(text, essay_type)


@mcp.prompt()
def intake_interview(language: str = "English") -> str:
    """Interview script to collect a candidate profile, in the candidate's language."""
    return (
        f"Interview the candidate in {language}, a few questions at a time, then call create_workspace.\n"
        "Ask for: full name; nationality and country of residence; date of birth; highest degree, university, "
        "graduation year; GPA and its scale (and class rank if known); target degree, field and 3-5 field keywords; "
        "target countries (or worldwide) and intake year; funding needed (Full/Partial/Any); English test, score, "
        "date and lowest band; other languages with CEFR level; years of full-time work and whether still employed; "
        "publications; 2-3 leadership moments with numbers; awards; volunteering; career goal and the problem at home "
        "they want to solve; whether they accept a 2-year return-home obligation; which papers they already hold "
        "(passport + expiry, degree certificate, transcript, CV, recommendation letters and how many, employment "
        "letter, police clearance). Do not guess missing answers; leave them out."
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
