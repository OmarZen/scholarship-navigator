"""
Scholarship Interview Preparation & Panel Mock Simulator.
Provides scholarship-specific interview questions, answer strategies using the STAR method,
and panel questions for Chevening, Fulbright, DAAD, and European faculties.
"""

from typing import Dict, Any, List, Optional
from .models import CandidateProfile


INTERVIEW_BANKS = {
    "chevening": {
        "title": "Chevening British Embassy Panel Interview Guide",
        "panel_format": "2-3 panellists (British Embassy diplomat, Chevening alumnus, British Council director). Duration: 25-35 minutes.",
        "questions": [
            {
                "category": "Diplomatic & Bilateral Relevance",
                "question": "Why should the British Government invest taxpayer funds in your master's degree rather than another candidate?",
                "strategy": "Connect your field directly to UK-home country priority sectors (e.g. green transition, governance, STEM innovation). Emphasize how you will return and serve as a bridge for bilateral collaboration."
            },
            {
                "category": "Leadership STAR Probe",
                "question": "In your leadership essay, you mentioned leading a major project. Describe a moment of severe interpersonal conflict or resistance during that project. How did you resolve it?",
                "strategy": "Do not repeat the essay verbatim. Provide fresh backstage details: What was the emotional challenge? What exact negotiation tactics did you use? What was the measurable outcome?"
            },
            {
                "category": "Course Selection Defense",
                "question": "You chose 3 different UK universities. Which one is your top choice, and why is this specific curriculum superior to programs in the US, Germany, or your home country?",
                "strategy": "Name specific modules, lab equipment, or professors at your 1st choice university. Explain why the 1-year intensive UK master's model accelerates your career."
            },
            {
                "category": "The Return & Brain Drain Test",
                "question": "What if you are offered a high-paying job in London immediately upon graduation? Will you stay in the UK?",
                "strategy": "ABSOLUTE RED LINE: You must firmly state your legal and moral commitment to return home for at least 2 years. Explain that your career vision is in your home country and staying would violate the Chevening mission."
            },
            {
                "category": "Networking Value Proposition",
                "question": "Chevening has an alumni network of over 55,000 leaders. What tangible value will you contribute to the Chevening alumni community?",
                "strategy": "Give a concrete example: mentoring incoming scholars, organizing regional tech workshops, or facilitating cross-border research partnerships."
            }
        ],
        "winning_questions_to_ask_panel": [
            "In your experience, what common traits distinguish the Chevening scholars who go on to achieve the most transformative impact in their home ministries or industries?",
            "How does the British Embassy in our country hope to leverage the Chevening alumni network over the next 5 years in our national priority sectors?"
        ]
    },
    "fulbright": {
        "title": "Fulbright Foreign Student Selection Interview Guide",
        "panel_format": "Binational selection committee / AMIDEAST / US Embassy cultural affairs officers. Duration: 20-30 minutes.",
        "questions": [
            {
                "category": "Cultural Ambassadorship",
                "question": "Fulbright is fundamentally a cultural exchange initiative, not merely an academic grant. How will you represent your home culture to Americans?",
                "strategy": "Discuss community engagement: participating in university cultural nights, giving presentations at local schools, cooking traditional food, and correcting misconceptions."
            },
            {
                "category": "Academic Study Objectives",
                "question": "How will the American graduate seminar system specifically benefit your research compared to European or local universities?",
                "strategy": "Emphasize interdisciplinary flexibility, access to cutting-edge research laboratories, and diverse peer cohorts."
            },
            {
                "category": "Home Country Re-integration",
                "question": "Under the J-1 visa, you must return home for at least 2 years. What concrete institutional role or policy reform will you target upon your return?",
                "strategy": "Name specific government ministries, research institutes, or NGOs where your newly acquired skills will be deployed."
            }
        ],
        "winning_questions_to_ask_panel": [
            "What advice would you give a Fulbrighter on balancing intensive graduate research with active cultural ambassadorship in American communities?"
        ]
    },
    "general": {
        "title": "International Postgraduate Scholarship Interview Master Guide",
        "panel_format": "Academic professors and scholarship administrators. Duration: 20-30 minutes.",
        "questions": [
            {
                "category": "Elevator Pitch",
                "question": "Tell us about yourself and why you are sitting in front of us today.",
                "strategy": "Follow the 'Past-Present-Future' formula in 90 seconds: 1) What academic/practical foundation you built, 2) The challenge you are currently solving, 3) Why this scholarship is the indispensable bridge to your future impact."
            },
            {
                "category": "Academic Vigor",
                "question": "Explain your undergraduate thesis or research project in simple terms to someone who is not a specialist in your field.",
                "strategy": "Use an everyday analogy. State the core problem, your method, and why the result matters in the real world."
            },
            {
                "category": "Resilience & Adaptability",
                "question": "Studying abroad can involve culture shock, loneliness, and academic stress. How have you handled severe adversity in the past?",
                "strategy": "Cite a genuine personal or professional challenge. Show emotional maturity, proactive support-seeking, and mental resilience."
            }
        ],
        "winning_questions_to_ask_panel": [
            "What academic or career pathways have previous recipients of this scholarship pursued most successfully?"
        ]
    }
}


def get_interview_prep(scholarship_id: str) -> Dict[str, Any]:
    s_clean = scholarship_id.strip().lower()
    if "chevening" in s_clean:
        return INTERVIEW_BANKS["chevening"]
    elif "fulbright" in s_clean:
        return INTERVIEW_BANKS["fulbright"]
    else:
        return INTERVIEW_BANKS["general"]

