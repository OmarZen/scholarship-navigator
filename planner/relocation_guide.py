"""
Post-Award Visa, Housing & Relocation Navigator.
Provides step-by-step visa dossier checklists, verified student accommodation platforms,
and arrival week orientation protocols.
"""

from typing import Dict, Any, List


RELOCATION_GUIDES = {
    "germany": {
        "country": "Germany",
        "visa_name": "National Visa for Study Purposes (Visum zu Studienzwecken - § 16b AufenthG)",
        "embassy_system": "TLScontact / German Embassy Consular Section",
        "visa_documents": [
            "Valid passport (at least 2 blank pages, valid for 1+ year)",
            "Official DAAD / Scholarship Award Certificate OR Sperrkonto confirmation (€11,904)",
            "Unconditional or conditional admission letter from German university",
            "Certified academic transcripts and degree certificates in English or German",
            "Proof of German statutory health insurance (TK, Barmer, or Mawista/Dr-Walter for visa stage)",
            "Cover Letter / Motivation Letter explaining choice of study in Germany"
        ],
        "housing_platforms": [
            "Studierendenwerk (Public University Dorms - apply months in advance!): www.studentenwerke.de",
            "WG-Gesucht (Shared apartments & flatshares): www.wg-gesucht.de",
            "ImmoScout24 & Immowelt: www.immobilienscout24.de"
        ],
        "arrival_checklist": [
            "Day 1-7: Register your address at the local Town Hall / Residents' Registration Office (Bürgeramt / Einwohnermeldeamt) to get your Meldebescheinigung.",
            "Day 3-10: Activate your blocked bank account (Expatrio / Coracle / Fintiba) using your Meldebescheinigung to start receiving monthly €992 payouts.",
            "Day 5-14: Complete physical matriculation at the university International Office and collect your Semesterticket (public transit pass).",
            "Month 2-3: Convert your entry visa into a formal Residence Permit (Aufenthaltstitel) at the Ausländerbehörde (Foreigners' Authority)."
        ]
    },
    "united kingdom": {
        "country": "United Kingdom",
        "visa_name": "Student Visa (formerly Tier 4 General Student)",
        "embassy_system": "VFS Global / UK Visas and Immigration (UKVI)",
        "visa_documents": [
            "Confirmation of Acceptance for Studies (CAS) number issued by your UK university",
            "Valid passport",
            "Chevening or scholarship official sponsorship letter",
            "Tuberculosis (TB) test certificate from an approved UKVI clinic",
            "Academic certificates and transcripts listed on your CAS"
        ],
        "housing_platforms": [
            "University On-Campus Halls of Residence (Apply as soon as you receive conditional offer)",
            "Unite Students: www.unitestudents.com",
            "Student.com: www.student.com",
            "SpareRoom UK (flatshares): www.spareroom.co.uk"
        ],
        "arrival_checklist": [
            "Collect your Biometric Residence Permit (BRP) or verify your digital eVisa status.",
            "Complete on-campus university in-person identity verification.",
            "Open a UK digital or high-street bank account (Monzo, Revolut, Barclays, HSBC).",
            "Register with a local National Health Service (NHS) General Practitioner (GP) doctor."
        ]
    },
    "netherlands": {
        "country": "Netherlands",
        "visa_name": "MVV Entry Visa & VVR Student Residence Permit",
        "embassy_system": "Applied directly by the Dutch university to the IND (Immigration and Naturalisation Service)",
        "visa_documents": [
            "The Dutch university applies for your visa on your behalf directly to the IND",
            "Valid passport copy",
            "Proof of financial means (~€1,050/month) or official scholarship award letter",
            "Antecedents Certificate (declaration of no criminal record)"
        ],
        "housing_platforms": [
            "DUWO / ROOM.nl (Largest Dutch student housing portal): www.room.nl",
            "SSH Student Housing: www.sshxl.nl",
            "Kamernet (Private rentals): www.kamernet.nl",
            "WARNING: The Netherlands faces an acute housing crisis. Never travel without verified housing contracts!"
        ],
        "arrival_checklist": [
            "Collect your Residence Permit card at the designated IND desk.",
            "Register at the local municipality (Gemeente) to receive your BSN (Citizen Service Number).",
            "Open a Dutch bank account (ABN AMRO, ING, Rabobank).",
            "Purchase mandatory Dutch private health insurance (Aon Student Insurance)."
        ]
    },
    "france": {
        "country": "France",
        "visa_name": "VLS-TS Long-Stay Student Visa (Visa de Long Séjour valant Titre de Séjour)",
        "embassy_system": "Campus France & France-Visas portal",
        "visa_documents": [
            "Campus France pre-consular validation and acceptance receipt",
            "Proof of financial resources (€615/month minimum) or Eiffel scholarship certificate",
            "Proof of accommodation for the first 3 months in France",
            "Diplomas and official French/English certified translations"
        ],
        "housing_platforms": [
            "CROUS (State-subsidized university student residences): www.messervices.etudiant.gouv.fr",
            "Studapart (University partner platform): www.studapart.com",
            "Lokaviz (CROUS student flatshare portal): www.lokaviz.fr"
        ],
        "arrival_checklist": [
            "Validate your VLS-TS visa online on the ANEF portal within 3 months of arrival.",
            "Register for French Social Security (L'Assurance Maladie - 100% free healthcare): etudiant-etranger.ameli.fr",
            "Apply for CAF Housing Aid (Aide Personnalisée au Logement - APL) to receive €100-€250/month rent reimbursement!"
        ]
    }
}


def get_relocation_guide(country_name: str) -> Dict[str, Any]:
    c_clean = country_name.strip().lower()
    for key, guide in RELOCATION_GUIDES.items():
        if key in c_clean or c_clean in key:
            return guide
    return RELOCATION_GUIDES["germany"]

