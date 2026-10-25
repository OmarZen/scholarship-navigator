"""
Cost of Attendance & Scholarship Financial Gap Calculator.
Calculates the exact out-of-pocket deficit and legal visa proof-of-funds requirements
for full vs partial scholarship scenarios.
"""

from typing import Dict, Any, Optional

COUNTRY_FINANCIAL_THRESHOLDS = {
    "germany": {
        "currency": "EUR",
        "annual_living_costs": 11904.0,
        "monthly_living_costs": 992.0,
        "blocked_account_name": "Sperrkonto (Blocked Bank Account)",
        "mandatory_legal_proof": 11904.0,
        "average_public_tuition": 350.0,
        "average_private_tuition": 12000.0,
        "health_insurance_annual": 1400.0,
        "flight_estimate": 700.0
    },
    "united kingdom": {
        "currency": "GBP",
        "annual_living_costs": 11000.0,
        "monthly_living_costs": 1023.0,
        "blocked_account_name": "28-Day Bank Statement Balance",
        "mandatory_legal_proof": 11000.0,
        "average_public_tuition": 22000.0,
        "average_private_tuition": 28000.0,
        "health_insurance_annual": 776.0,
        "flight_estimate": 600.0
    },
    "netherlands": {
        "currency": "EUR",
        "annual_living_costs": 13000.0,
        "monthly_living_costs": 1083.0,
        "blocked_account_name": "IND Proof of Living Means Deposit",
        "mandatory_legal_proof": 12600.0,
        "average_public_tuition": 16000.0,
        "average_private_tuition": 18000.0,
        "health_insurance_annual": 800.0,
        "flight_estimate": 650.0
    },
    "france": {
        "currency": "EUR",
        "annual_living_costs": 9000.0,
        "monthly_living_costs": 750.0,
        "blocked_account_name": "French Visa Financial Guarantee (€615/mo)",
        "mandatory_legal_proof": 7380.0,
        "average_public_tuition": 3770.0,
        "average_private_tuition": 14000.0,
        "health_insurance_annual": 0.0, # Sécurité sociale is free
        "flight_estimate": 600.0
    },
    "denmark": {
        "currency": "EUR",
        "annual_living_costs": 12000.0,
        "monthly_living_costs": 1000.0,
        "blocked_account_name": "SIRI Financial Solvency Proof",
        "mandatory_legal_proof": 11000.0,
        "average_public_tuition": 12000.0,
        "average_private_tuition": 15000.0,
        "health_insurance_annual": 0.0,
        "flight_estimate": 650.0
    },
    "finland": {
        "currency": "EUR",
        "annual_living_costs": 10000.0,
        "monthly_living_costs": 833.0,
        "blocked_account_name": "Migri Residence Permit Account (€560/mo)",
        "mandatory_legal_proof": 6720.0,
        "average_public_tuition": 12000.0,
        "average_private_tuition": 14000.0,
        "health_insurance_annual": 400.0,
        "flight_estimate": 700.0
    },
    "sweden": {
        "currency": "SEK",
        "annual_living_costs": 123768.0,
        "monthly_living_costs": 10314.0,
        "blocked_account_name": "Migrationsverket Maintenance Proof",
        "mandatory_legal_proof": 123768.0,
        "average_public_tuition": 110000.0,
        "average_private_tuition": 130000.0,
        "health_insurance_annual": 0.0,
        "flight_estimate": 7000.0
    },
    "norway": {
        "currency": "NOK",
        "annual_living_costs": 151690.0,
        "monthly_living_costs": 12640.0,
        "blocked_account_name": "UDI Student Escrow Deposit",
        "mandatory_legal_proof": 151690.0,
        "average_public_tuition": 150000.0,
        "average_private_tuition": 170000.0,
        "health_insurance_annual": 0.0,
        "flight_estimate": 7500.0
    },
    "australia": {
        "currency": "AUD",
        "annual_living_costs": 29710.0,
        "monthly_living_costs": 2475.0,
        "blocked_account_name": "Home Affairs Genuine Student Funds",
        "mandatory_legal_proof": 29710.0,
        "average_public_tuition": 34000.0,
        "average_private_tuition": 40000.0,
        "health_insurance_annual": 650.0,
        "flight_estimate": 1800.0
    },
    "canada": {
        "currency": "CAD",
        "annual_living_costs": 20635.0,
        "monthly_living_costs": 1720.0,
        "blocked_account_name": "IRCC Living Threshold / GIC Deposit",
        "mandatory_legal_proof": 20635.0,
        "average_public_tuition": 24000.0,
        "average_private_tuition": 32000.0,
        "health_insurance_annual": 800.0,
        "flight_estimate": 1200.0
    },
    "italy": {
        "currency": "EUR",
        "annual_living_costs": 8500.0,
        "monthly_living_costs": 708.0,
        "blocked_account_name": "Italian Visa Bank Means (€468/mo)",
        "mandatory_legal_proof": 6080.0,
        "average_public_tuition": 1500.0,
        "average_private_tuition": 8000.0,
        "health_insurance_annual": 150.0,
        "flight_estimate": 500.0
    }
}


def calculate_financial_gap(
    country: str,
    scholarship_covers_tuition: bool = True,
    monthly_stipend_received: float = 0.0,
    stipend_duration_months: int = 12,
    scholarship_covers_flights: bool = False,
    scholarship_covers_insurance: bool = False,
    is_private_university: bool = False
) -> Dict[str, Any]:
    c_key = country.strip().lower()
    info = COUNTRY_FINANCIAL_THRESHOLDS.get(c_key)
    if not info:
        # Default fallback (Western Europe EUR baseline)
        info = COUNTRY_FINANCIAL_THRESHOLDS["germany"]

    curr = info["currency"]
    tuition = 0.0 if scholarship_covers_tuition else (info["average_private_tuition"] if is_private_university else info["average_public_tuition"])
    living = info["annual_living_costs"]
    insurance = 0.0 if scholarship_covers_insurance else info["health_insurance_annual"]
    flights = 0.0 if scholarship_covers_flights else info["flight_estimate"]

    total_gross_cost = tuition + living + insurance + flights
    scholarship_cash_inflow = monthly_stipend_received * stipend_duration_months
    net_gap = max(0.0, total_gross_cost - scholarship_cash_inflow)

    is_fully_covered = (net_gap == 0.0)
    visa_proof_required = max(0.0, info["mandatory_legal_proof"] - scholarship_cash_inflow)

    return {
        "country": country.title(),
        "currency": curr,
        "estimated_gross_annual_cost": round(total_gross_cost, 2),
        "breakdown": {
            "tuition_out_of_pocket": round(tuition, 2),
            "living_expenses_annual": round(living, 2),
            "health_insurance": round(insurance, 2),
            "travel_flights": round(flights, 2)
        },
        "scholarship_funding_inflow": round(scholarship_cash_inflow, 2),
        "net_out_of_pocket_deficit": round(net_gap, 2),
        "is_fully_funded": is_fully_covered,
        "visa_compliance": {
            "mechanism": info["blocked_account_name"],
            "legal_proof_threshold": round(info["mandatory_legal_proof"], 2),
            "remaining_amount_to_freeze_in_bank": round(visa_proof_required, 2)
        }
    }
