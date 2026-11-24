from datetime import datetime
from typing import Dict, Any, List, Optional
from models.schemas import DocumentAgentOutput, PolicyAgentOutput
from services.gemini_service import generate_structured_json
from utils.logger import logger

SYSTEM_PROMPT = """
You are Agent 2: Policy Verification Agent for InsuraFlow AI.
Compare the extracted motor insurance claim data against the retrieved policy record from the database.
Rules:
1. Verify whether the policy exists and whether the accident_date falls strictly within policy_start_date and policy_end_date (inclusive).
2. Check if claimed_amount is within coverage_limit (IDV) and note the compulsory deductible.
3. Identify any policy exclusions triggered by the damage description or circumstances.
4. Check which required_documents from the policy are missing based on uploaded filenames and extracted document text.
5. Never invent policy clauses or coverage numbers. Only cite clauses present in the database policy record. If no policy record exists, mark policy_found=false and mark policy fields as 'Unavailable'.
"""


def _parse_date(date_str: str) -> Optional[datetime]:
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except Exception:
            continue
    return None


def _check_missing_docs(required_docs: List[str], uploaded_names: List[str], damage_desc: str) -> List[str]:
    lower_files = " ".join(uploaded_names).lower()
    missing = []
    for req in required_docs:
        r_low = req.lower()
        if "claim form" in r_low and not any(k in lower_files for k in ["claim", "form", "fnol"]):
            missing.append(req)
        elif ("estimate" in r_low or "invoice" in r_low) and not any(k in lower_files for k in ["estimate", "invoice", "bill", "repair", "garage"]):
            missing.append(req)
        elif ("rc" in r_low or "registration" in r_low) and not any(k in lower_files for k in ["rc", "registration", "vehicle"]):
            missing.append(req)
        elif ("license" in r_low or "dl" in r_low) and not any(k in lower_files for k in ["dl", "license", "licence", "driver"]):
            missing.append(req)
        elif ("fir" in r_low or "police" in r_low):
            # FIR required for theft, third-party injury, or major collision (> INR 1,00,000)
            if not any(k in lower_files for k in ["fir", "police", "ddr", "gd"]):
                missing.append(req)
    return missing


def run_policy_agent(
    doc_output: DocumentAgentOutput,
    policy_record: Optional[Dict[str, Any]],
    demo_mode: bool = False,
) -> PolicyAgentOutput:
    if not policy_record:
        return PolicyAgentOutput(
            policy_found=False,
            policy_valid=False,
            coverage_applicable=False,
            coverage_type="Unavailable",
            policy_start_date="Unavailable",
            policy_end_date="Unavailable",
            coverage_limit=0.0,
            deductible=0.0,
            relevant_clauses=[],
            policy_findings=[
                f"No active or historical policy record found matching policy number '{doc_output.policy_number}'."
            ],
            missing_documents=["Valid Policy Schedule"],
            explanation="Policy verification could not confirm coverage because the policy number was not found in the policy repository.",
        )

    if not demo_mode:
        prompt = f"""
Extracted Claim Data:
{doc_output.model_dump_json(indent=2)}

Database Policy Record:
- Policy Number: {policy_record.get('policy_number')}
- Policyholder Name: {policy_record.get('policyholder_name')}
- Vehicle Number: {policy_record.get('vehicle_number')}
- Vehicle Model: {policy_record.get('vehicle_model')}
- Coverage Type: {policy_record.get('coverage_type')}
- Start Date: {policy_record.get('start_date')}
- End Date: {policy_record.get('end_date')}
- Coverage Limit / IDV (INR): {policy_record.get('coverage_limit')}
- Compulsory Deductible (INR): {policy_record.get('deductible')}
- Status: {policy_record.get('status')}
- Policy Clauses: {policy_record.get('clauses', [])}
- Exclusions: {policy_record.get('exclusions', [])}
- Required Documents: {policy_record.get('required_documents', [])}
"""
        return generate_structured_json(SYSTEM_PROMPT, prompt, PolicyAgentOutput)

    # Deterministic Demo Mode
    logger.info(f"[Demo Mode] Running Policy Verification Agent for {doc_output.policy_number}")
    start_str = policy_record.get("start_date", "")
    end_str = policy_record.get("end_date", "")
    acc_dt = _parse_date(doc_output.accident_date)
    start_dt = _parse_date(start_str)
    end_dt = _parse_date(end_str)

    findings: List[str] = []
    policy_valid = True

    if acc_dt and start_dt and end_dt:
        if acc_dt < start_dt or acc_dt > end_dt:
            policy_valid = False
            findings.append(
                f"Accident date ({doc_output.accident_date}) falls outside policy coverage period ({start_str} to {end_str})."
            )
    else:
        policy_valid = False
        findings.append("Unable to verify accident date against policy dates due to missing or invalid date format.")

    if policy_record.get("status", "").lower() != "active" and policy_valid:
        policy_valid = False
        findings.append(f"Policy status is recorded as '{policy_record.get('status')}'.")

    pol_veh = (policy_record.get("vehicle_number") or "").replace(" ", "").upper()
    clm_veh = (doc_output.vehicle_number or "").replace(" ", "").upper()
    if pol_veh and clm_veh and pol_veh != clm_veh:
        findings.append(
            f"Claimed vehicle registration ({clm_veh}) does not match insured vehicle ({pol_veh})."
        )

    cov_limit = float(policy_record.get("coverage_limit") or 0)
    deductible = float(policy_record.get("deductible") or 0)
    if doc_output.claimed_amount > cov_limit:
        findings.append(
            f"Claimed amount (INR {doc_output.claimed_amount:,.2f}) exceeds Insured Declared Value limit (INR {cov_limit:,.2f})."
        )

    missing_docs = _check_missing_docs(
        policy_record.get("required_documents", []),
        doc_output.detected_documents,
        doc_output.damage_description,
    )

    coverage_applicable = policy_valid and (pol_veh == clm_veh or not pol_veh)
    if coverage_applicable and not findings:
        explanation = (
            f"The reported accident date ({doc_output.accident_date}) falls within the active policy period "
            f"({start_str} to {end_str}) under {policy_record.get('coverage_type')} cover with IDV INR {cov_limit:,.0f}."
        )
    else:
        explanation = " ".join(findings) if findings else "Policy conditions require officer verification."

    return PolicyAgentOutput(
        policy_found=True,
        policy_valid=policy_valid,
        coverage_applicable=coverage_applicable,
        coverage_type=policy_record.get("coverage_type", "Comprehensive"),
        policy_start_date=start_str,
        policy_end_date=end_str,
        coverage_limit=cov_limit,
        deductible=deductible,
        relevant_clauses=policy_record.get("clauses", []),
        policy_findings=findings,
        missing_documents=missing_docs,
        explanation=explanation,
    )
