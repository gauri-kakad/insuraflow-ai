from datetime import datetime, timezone
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors

from database import get_database
from utils.security import hash_password
from utils.logger import logger
from workflows.graph import execute_claim_workflow


def _create_sample_pdf(filepath: Path, title: str, lines: list[str]) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(filepath), pagesize=A4)
    width, height = A4
    c.setFillColor(colors.HexColor("#0F2942"))
    c.rect(40, height - 80, width - 80, 42, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(54, height - 64, title)

    c.setFillColor(colors.HexColor("#1E293B"))
    y = height - 115
    for line in lines:
        if line.startswith("## "):
            y -= 8
            c.setFont("Helvetica-Bold", 11)
            c.drawString(45, y, line.replace("## ", ""))
            y -= 18
        else:
            c.setFont("Helvetica", 10)
            c.drawString(45, y, line)
            y -= 16
    c.save()


def generate_sample_documents() -> None:
    sample_dir = Path(__file__).resolve().parent.parent / "sample_docs"
    sample_dir.mkdir(parents=True, exist_ok=True)

    _create_sample_pdf(
        sample_dir / "Sample_Motor_Policy_MTR-2026-001.pdf",
        "MOTOR SHIELD COMPREHENSIVE POLICY SCHEDULE",
        [
            "## Policy Identification",
            "Policy Number: MTR-2026-001",
            "Policyholder Name: Rahul Sharma",
            "Registered Address: Camp Road, Amravati, Maharashtra 444602",
            "## Insured Vehicle Details",
            "Vehicle Registration Number: MH28AB1234",
            "Make & Model: Hyundai i20 Sportz 1.2 Petrol (2024)",
            "## Coverage & Limits",
            "Coverage Type: Comprehensive Private Car Package Policy",
            "Policy Period: 2026-01-15 to 2027-01-14",
            "Insured Declared Value (IDV): INR 5,00,000",
            "Compulsory Deductible: INR 2,000",
            "## Key Policy Clauses",
            "Clause 1.1: Accidental external means damage covered up to IDV less compulsory deductible.",
            "Clause 3.2: Zero Depreciation add-on active for fiber, rubber, and glass parts.",
            "Exclusion 4.1: Consequential mechanical breakdown or driving without valid license excluded.",
        ],
    )

    _create_sample_pdf(
        sample_dir / "Sample_Garage_Estimate_CLM-2026-1001.pdf",
        "APEX AUTOWORKS - AUTHORIZED REPAIR ESTIMATE & INVOICE",
        [
            "## Garage & Invoice Details",
            "Invoice Reference: INV-2026-4410",
            "Policy Number: MTR-2026-001",
            "Customer Name: Rahul Sharma",
            "Vehicle Registration: MH28AB1234 (Hyundai i20)",
            "Accident Date: 2026-11-20",
            "## Itemized Repair Estimate",
            "1. Front Bumper Assembly Replacement & Paint: INR 18,500",
            "2. Left & Right LED Headlamp Assembly: INR 19,000",
            "3. Front Grille & Radiator Support Alignment: INR 5,000",
            "4. Labor, Calibration & GST: INR 2,500",
            "## Summary",
            "Grand Total Estimate: INR 45,000",
        ],
    )

    _create_sample_pdf(
        sample_dir / "Sample_Duplicate_Invoice_Test.pdf",
        "METRO MOTORS - REPAIR INVOICE (TEST DUPLICATE TRIGGER)",
        [
            "## Garage & Invoice Details",
            "Invoice Reference: INV-9981-DUP",
            "Policy Number: MTR-2026-003",
            "Customer Name: Vikram Malhotra",
            "Vehicle Registration: DL08CA7721 (Honda City)",
            "Accident Date: 2026-11-21",
            "## Itemized Repair Estimate",
            "1. Rear Quarter Panel & Bumper Replacement: INR 62,000",
            "2. Tail Lamp Cluster & Trunk Lid Repair: INR 33,000",
            "Grand Total Estimate: INR 95,000",
        ],
    )


def seed_database(force_reset: bool = False) -> dict:
    db = get_database()
    generate_sample_documents()

    if force_reset:
        for col in ["users", "policies", "claims", "agent_executions", "assessments", "audit_logs"]:
            db[col].delete_many({})

    # 1. Seed Users
    if db.users.count_documents({}) == 0:
        users = [
            {
                "user_id": "USR-001",
                "name": "Arjun Mehta",
                "email": "officer@insuraflow.ai",
                "hashed_password": hash_password("Officer@2026"),
                "role": "Senior Claims Officer",
                "department": "Motor Claims Adjudication",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "user_id": "USR-002",
                "name": "Kavita Deshmukh",
                "email": "siu@insuraflow.ai",
                "hashed_password": hash_password("Investigator@2026"),
                "role": "Special Investigation Unit (SIU) Lead",
                "department": "Fraud & Risk Analytics",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        ]
        db.users.insert_many(users)

    # 2. Seed Synthetic Policies
    if db.policies.count_documents({}) == 0:
        policies = [
            {
                "policy_number": "MTR-2026-001",
                "policyholder_name": "Rahul Sharma",
                "vehicle_number": "MH28AB1234",
                "vehicle_model": "Hyundai i20",
                "coverage_type": "Comprehensive",
                "start_date": "2026-01-15",
                "end_date": "2027-01-14",
                "coverage_limit": 500000,
                "deductible": 2000,
                "status": "Active",
                "clauses": [
                    "Clause 1.1: Accidental external impact damage covered up to IDV.",
                    "Clause 2.4: Compulsory deductible of INR 2,000 applies per claim.",
                ],
                "exclusions": [
                    "Exclusion 4.1: Driving under influence or without valid license.",
                    "Exclusion 4.3: Normal wear and tear or mechanical failure.",
                ],
                "required_documents": ["Claim Form", "Repair Estimate / Invoice", "Registration Certificate (RC)", "Driving License"],
            },
            {
                "policy_number": "MTR-2026-002",
                "policyholder_name": "Ananya Verma",
                "vehicle_number": "KA03MJ8842",
                "vehicle_model": "Tata Nexon EV",
                "coverage_type": "Comprehensive + Battery Protect",
                "start_date": "2026-11-10",
                "end_date": "2027-11-09",
                "coverage_limit": 350000,
                "deductible": 2500,
                "status": "Active",
                "clauses": [
                    "Clause 1.1: Accidental damage covered up to IDV INR 3,50,000.",
                    "Clause 5.2: Physical surveyor inspection mandatory for claims > INR 1,00,000.",
                ],
                "exclusions": ["Exclusion 4.2: Off-road racing or commercial hire usage."],
                "required_documents": ["Claim Form", "Repair Estimate / Invoice", "Registration Certificate (RC)", "Driving License"],
            },
            {
                "policy_number": "MTR-2026-003",
                "policyholder_name": "Vikram Malhotra",
                "vehicle_number": "DL08CA7721",
                "vehicle_model": "Honda City",
                "coverage_type": "Comprehensive",
                "start_date": "2026-03-01",
                "end_date": "2027-02-28",
                "coverage_limit": 650000,
                "deductible": 2000,
                "status": "Active",
                "clauses": [
                    "Clause 1.1: Accidental damage covered up to IDV INR 6,50,000.",
                    "Clause 6.1: Duplicate or altered repair invoices void claim eligibility.",
                ],
                "exclusions": ["Exclusion 4.5: Pre-existing structural damage prior to policy inception."],
                "required_documents": ["Claim Form", "Repair Estimate / Invoice", "Registration Certificate (RC)", "Driving License"],
            },
            {
                "policy_number": "MTR-2026-004",
                "policyholder_name": "Priya Nair",
                "vehicle_number": "KL07CD5519",
                "vehicle_model": "Maruti Suzuki Baleno",
                "coverage_type": "Comprehensive",
                "start_date": "2026-05-01",
                "end_date": "2027-04-30",
                "coverage_limit": 480000,
                "deductible": 1500,
                "status": "Active",
                "clauses": [
                    "Clause 1.1: Accidental damage covered up to IDV INR 4,80,000.",
                    "Clause 3.4: Police FIR / General Diary entry mandatory for highway collisions.",
                ],
                "exclusions": ["Exclusion 4.1: Unlicensed driver operation."],
                "required_documents": ["Claim Form", "Repair Estimate / Invoice", "Registration Certificate (RC)", "Driving License", "Police FIR"],
            },
            {
                "policy_number": "MTR-2026-005",
                "policyholder_name": "Suresh Kulkarni",
                "vehicle_number": "MH12PQ9034",
                "vehicle_model": "Mahindra XUV300",
                "coverage_type": "Comprehensive",
                "start_date": "2025-11-01",
                "end_date": "2026-10-31",
                "coverage_limit": 600000,
                "deductible": 2000,
                "status": "Expired",
                "clauses": [
                    "Clause 1.0: Coverage strictly applies only during active policy dates.",
                ],
                "exclusions": ["Exclusion 1.2: Incidents occurring post policy expiration."],
                "required_documents": ["Claim Form", "Repair Estimate / Invoice", "Registration Certificate (RC)"],
            },
        ]
        db.policies.insert_many(policies)

    # 3. Seed Historical & 5 Demo Motor Claims
    if db.claims.count_documents({}) == 0:
        demo_claims = [
            # Historical reference claim used for duplicate invoice detection
            {
                "claim_id": "CLM-2026-0914",
                "policyholder_name": "Vikram Malhotra",
                "policyholder_email": "vikram.m@example.com",
                "policyholder_phone": "+91-98110-44210",
                "policy_number": "MTR-2026-003",
                "vehicle_number": "DL08CA7721",
                "vehicle_model": "Honda City",
                "accident_date": "2026-09-12",
                "accident_time": "19:30",
                "accident_location": "Gurugram Cyber Hub",
                "claimed_amount": 92000,
                "estimated_damage_amount": 92000,
                "invoice_reference": "INV-9981-DUP",
                "invoice_numbers": ["INV-9981-DUP"],
                "damage_description": "Rear bumper, tail lamp cluster, and trunk lid collision damage.",
                "documents": [
                    {"doc_id": "DOC-H01", "original_name": "Claim_Form_0914.pdf", "doc_category": "claim_form"},
                    {"doc_id": "DOC-H02", "original_name": "Garage_Invoice_INV-9981-DUP.pdf", "doc_category": "invoice"},
                    {"doc_id": "DOC-H03", "original_name": "RC_and_DL_Copy.pdf", "doc_category": "kyc"},
                ],
                "status": "Settled",
                "risk_level": "Low",
                "risk_score": 14,
                "submitted_at": "2026-09-14T10:15:00+00:00",
                "processing_time_ms": 1820,
            },
            # Scenario 1: Low-Risk Claim
            {
                "claim_id": "CLM-2026-1001",
                "policyholder_name": "Rahul Sharma",
                "policyholder_email": "rahul.sharma@example.com",
                "policyholder_phone": "+91-98220-11234",
                "policy_number": "MTR-2026-001",
                "vehicle_number": "MH28AB1234",
                "vehicle_model": "Hyundai i20",
                "accident_date": "2026-11-20",
                "accident_time": "09:45",
                "accident_location": "Amravati",
                "claimed_amount": 45000,
                "estimated_damage_amount": 45000,
                "invoice_reference": "INV-2026-4410",
                "invoice_numbers": ["INV-2026-4410"],
                "damage_description": "Front bumper and headlight damage caused by minor intersection collision.",
                "documents": [
                    {"doc_id": "DOC-101A", "original_name": "Motor_Claim_Form_1001.pdf", "doc_category": "claim_form"},
                    {"doc_id": "DOC-101B", "original_name": "Apex_Garage_Estimate_INV-2026-4410.pdf", "doc_category": "invoice"},
                    {"doc_id": "DOC-101C", "original_name": "Vehicle_RC_MH28AB1234.pdf", "doc_category": "rc"},
                    {"doc_id": "DOC-101D", "original_name": "Driving_License_Rahul.pdf", "doc_category": "license"},
                ],
                "status": "Submitted",
                "submitted_at": "2026-11-21T08:30:00+00:00",
            },
            # Scenario 2: Medium-Risk Claim (High Claim-to-IDV ratio + Early Policy Inception)
            {
                "claim_id": "CLM-2026-1002",
                "policyholder_name": "Ananya Verma",
                "policyholder_email": "ananya.verma@example.com",
                "policyholder_phone": "+91-99001-77321",
                "policy_number": "MTR-2026-002",
                "vehicle_number": "KA03MJ8842",
                "vehicle_model": "Tata Nexon EV",
                "accident_date": "2026-11-18",
                "accident_time": "22:15",
                "accident_location": "Bengaluru Outer Ring Road",
                "claimed_amount": 285000,
                "estimated_damage_amount": 285000,
                "invoice_reference": "INV-EV-7720",
                "invoice_numbers": ["INV-EV-7720"],
                "damage_description": "Front subframe, cooling assembly, and underbody battery shield impact damage.",
                "documents": [
                    {"doc_id": "DOC-102A", "original_name": "FNOL_Claim_Form_1002.pdf", "doc_category": "claim_form"},
                    {"doc_id": "DOC-102B", "original_name": "EV_Service_Repair_Estimate.pdf", "doc_category": "invoice"},
                    {"doc_id": "DOC-102C", "original_name": "RC_KA03MJ8842.pdf", "doc_category": "rc"},
                    {"doc_id": "DOC-102D", "original_name": "DL_Ananya_Verma.pdf", "doc_category": "license"},
                ],
                "status": "Submitted",
                "submitted_at": "2026-11-21T11:10:00+00:00",
            },
            # Scenario 3: High-Risk Claim with Duplicate Invoice Indicator
            {
                "claim_id": "CLM-2026-1003",
                "policyholder_name": "Vikram Malhotra",
                "policyholder_email": "vikram.m@example.com",
                "policyholder_phone": "+91-98110-44210",
                "policy_number": "MTR-2026-003",
                "vehicle_number": "DL08CA7721",
                "vehicle_model": "Honda City",
                "accident_date": "2026-11-21",
                "accident_time": "20:10",
                "accident_location": "New Delhi Ring Road",
                "claimed_amount": 95000,
                "estimated_damage_amount": 95000,
                "invoice_reference": "INV-9981-DUP",
                "invoice_numbers": ["INV-9981-DUP"],
                "damage_description": "Rear quarter panel, bumper replacement, and tail lamp cluster damage.",
                "documents": [
                    {"doc_id": "DOC-103A", "original_name": "Claim_Form_1003.pdf", "doc_category": "claim_form"},
                    {"doc_id": "DOC-103B", "original_name": "Metro_Motors_Invoice_INV-9981-DUP.pdf", "doc_category": "invoice"},
                    {"doc_id": "DOC-103C", "original_name": "Registration_DL08CA7721.pdf", "doc_category": "rc"},
                    {"doc_id": "DOC-103D", "original_name": "Driver_License_Vikram.pdf", "doc_category": "license"},
                ],
                "status": "Submitted",
                "submitted_at": "2026-11-22T09:05:00+00:00",
            },
            # Scenario 4: Missing Supporting Documents
            {
                "claim_id": "CLM-2026-1004",
                "policyholder_name": "Priya Nair",
                "policyholder_email": "priya.nair@example.com",
                "policyholder_phone": "+91-98470-33219",
                "policy_number": "MTR-2026-004",
                "vehicle_number": "KL07CD5519",
                "vehicle_model": "Maruti Suzuki Baleno",
                "accident_date": "2026-11-22",
                "accident_time": "14:20",
                "accident_location": "Kochi NH-66 Bypass",
                "claimed_amount": 68000,
                "estimated_damage_amount": 68000,
                "invoice_reference": "INV-KCH-309",
                "invoice_numbers": ["INV-KCH-309"],
                "damage_description": "Left side doors and fender denting following highway lane-merge collision.",
                "documents": [
                    {"doc_id": "DOC-104A", "original_name": "Claim_Form_1004.pdf", "doc_category": "claim_form"},
                    {"doc_id": "DOC-104B", "original_name": "Registration_KL07CD5519.pdf", "doc_category": "rc"},
                ],
                "status": "Submitted",
                "submitted_at": "2026-11-23T07:45:00+00:00",
            },
            # Scenario 5: Policy Validity Issue (Expired Policy)
            {
                "claim_id": "CLM-2026-1005",
                "policyholder_name": "Suresh Kulkarni",
                "policyholder_email": "suresh.k@example.com",
                "policyholder_phone": "+91-98230-66109",
                "policy_number": "MTR-2026-005",
                "vehicle_number": "MH12PQ9034",
                "vehicle_model": "Mahindra XUV300",
                "accident_date": "2026-11-18",
                "accident_time": "16:50",
                "accident_location": "Pune Mumbai Expressway",
                "claimed_amount": 112000,
                "estimated_damage_amount": 112000,
                "invoice_reference": "INV-PUN-882",
                "invoice_numbers": ["INV-PUN-882"],
                "damage_description": "Front bonnet, grille, and radiator frame damage.",
                "documents": [
                    {"doc_id": "DOC-105A", "original_name": "Claim_Form_1005.pdf", "doc_category": "claim_form"},
                    {"doc_id": "DOC-105B", "original_name": "Repair_Estimate_Pune.pdf", "doc_category": "invoice"},
                    {"doc_id": "DOC-105C", "original_name": "RC_MH12PQ9034.pdf", "doc_category": "rc"},
                ],
                "status": "Submitted",
                "submitted_at": "2026-11-23T14:20:00+00:00",
            },
        ]
        db.claims.insert_many(demo_claims)

        # Execute the multi-agent workflow in Deterministic Demo Mode on the 5 new claims so dashboard & history are immediately populated
        for cid in ["CLM-2026-1001", "CLM-2026-1002", "CLM-2026-1003", "CLM-2026-1004", "CLM-2026-1005"]:
            execute_claim_workflow(cid, demo_mode=True, triggered_by="Initial Seed Engine")

    logger.info("Database seeding verification complete.")
    return {
        "users": db.users.count_documents({}),
        "policies": db.policies.count_documents({}),
        "claims": db.claims.count_documents({}),
        "assessments": db.assessments.count_documents({}),
    }
