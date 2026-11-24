import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.schemas import DocumentAgentOutput, PolicyAgentOutput
from agents.policy_agent import run_policy_agent
from agents.fraud_agent import run_fraud_agent
from agents.assessment_agent import run_assessment_agent


def test_deterministic_agents_low_risk_flow():
    doc_out = DocumentAgentOutput(
        policyholder_name="Rahul Sharma",
        policy_number="MTR-2026-001",
        vehicle_number="MH28AB1234",
        vehicle_model="Hyundai i20",
        accident_date="2026-11-20",
        accident_location="Amravati",
        estimated_damage_amount=45000,
        claimed_amount=45000,
        damage_description="Front bumper damage",
        invoice_numbers=["INV-2026-4410"],
        detected_documents=["Claim_Form.pdf", "Repair_Invoice.pdf", "RC.pdf", "License.pdf"],
        missing_fields=[],
        confidence=0.95,
    )

    policy_rec = {
        "policy_number": "MTR-2026-001",
        "policyholder_name": "Rahul Sharma",
        "vehicle_number": "MH28AB1234",
        "coverage_type": "Comprehensive",
        "start_date": "2026-01-15",
        "end_date": "2027-01-14",
        "coverage_limit": 500000,
        "deductible": 2000,
        "status": "Active",
        "clauses": ["Clause 1.1: Accidental damage covered."],
        "exclusions": [],
        "required_documents": ["Claim Form", "Repair Invoice", "RC", "License"],
    }

    pol_out = run_policy_agent(doc_out, policy_rec, demo_mode=True)
    assert pol_out.policy_valid is True
    assert pol_out.coverage_applicable is True

    fraud_out = run_fraud_agent({"claim_id": "CLM-TEST-01"}, doc_out, pol_out, [], demo_mode=True)
    assert fraud_out.risk_level == "Low"
    assert fraud_out.requires_manual_review is True

    assess_out = run_assessment_agent({"claim_id": "CLM-TEST-01"}, doc_out, pol_out, fraud_out, demo_mode=True)
    assert assess_out.human_review_required is True
    assert assess_out.recommended_next_action == "Ready for Human Review"
    assert assess_out.estimated_eligible_amount == 43000.0


def test_duplicate_invoice_triggers_high_risk():
    doc_out = DocumentAgentOutput(
        policyholder_name="Vikram Malhotra",
        policy_number="MTR-2026-003",
        vehicle_number="DL08CA7721",
        vehicle_model="Honda City",
        accident_date="2026-11-21",
        accident_location="Delhi",
        claimed_amount=95000,
        invoice_numbers=["INV-9981-DUP"],
        detected_documents=["Claim_Form.pdf", "Invoice.pdf", "RC.pdf", "DL.pdf"],
        confidence=0.92,
    )
    pol_out = PolicyAgentOutput(
        policy_found=True,
        policy_valid=True,
        coverage_applicable=True,
        coverage_type="Comprehensive",
        policy_start_date="2026-03-01",
        policy_end_date="2027-02-28",
        coverage_limit=650000,
        deductible=2000,
    )
    historical = [{
        "claim_id": "CLM-2026-0914",
        "policy_number": "MTR-2026-003",
        "accident_date": "2026-09-12",
        "claimed_amount": 92000,
        "invoice_numbers": ["INV-9981-DUP"],
        "damage_description": "Rear collision",
    }]
    fraud_out = run_fraud_agent({"claim_id": "CLM-2026-1003"}, doc_out, pol_out, historical, demo_mode=True)
    assert fraud_out.risk_level == "High"
    assert fraud_out.risk_score >= 65
