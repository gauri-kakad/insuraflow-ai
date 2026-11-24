import re
from typing import Dict, Any, List
from models.schemas import DocumentAgentOutput
from services.document_processor import extract_claim_documents
from services.gemini_service import generate_structured_json
from utils.logger import logger

SYSTEM_PROMPT = """
You are Agent 1: Document Intelligence Agent for InsuraFlow AI, a motor insurance claims decision-support system.
Your task is to analyze extracted text from uploaded motor insurance claim documents alongside submitted intake metadata.
Rules:
1. Extract policyholder_name, policy_number, vehicle_number, vehicle_model, accident_date (YYYY-MM-DD), accident_time, accident_location, estimated_damage_amount, claimed_amount, damage_description, and any invoice_numbers.
2. Identify missing_fields if critical information is unreadable, blank, or contradictory across documents.
3. Add validation_notes if document values differ from intake form values (for example, different dates or amounts).
4. Never fabricate invoice numbers or details not supported by the text/intake.
5. Provide a realistic extraction confidence score between 0.0 and 1.0.
"""


def _extract_regex_fields(text: str) -> Dict[str, Any]:
    found: Dict[str, Any] = {}
    pol = re.search(r"\b(MTR-\d{4}-\d{3,6})\b", text, re.IGNORECASE)
    if pol:
        found["policy_number"] = pol.group(1).upper()

    veh = re.search(r"\b([A-Z]{2}\d{2}[A-Z]{1,2}\d{4})\b", text.replace(" ", ""), re.IGNORECASE)
    if veh:
        found["vehicle_number"] = veh.group(1).upper()

    inv = re.findall(r"\b(INV-[A-Z0-9-]+)\b", text, re.IGNORECASE)
    if inv:
        found["invoice_numbers"] = list(dict.fromkeys([i.upper() for i in inv]))

    amt = re.search(r"(?:Total|Claimed|Estimate|Grand Total)[^\d]{0,15}(?:INR|Rs\.?|₹)?\s*([\d,]+(?:\.\d{1,2})?)", text, re.IGNORECASE)
    if amt:
        try:
            found["extracted_amount"] = float(amt.group(1).replace(",", ""))
        except ValueError:
            pass

    dt = re.search(r"(?:Accident Date|Date of Loss|Incident Date)[:\s]+(\d{4}-\d{2}-\d{2})", text, re.IGNORECASE)
    if dt:
        found["accident_date"] = dt.group(1)

    return found


def run_document_agent(claim: Dict[str, Any], demo_mode: bool = False) -> DocumentAgentOutput:
    docs = claim.get("documents", [])
    extraction = extract_claim_documents(docs)
    combined_text = extraction.get("combined_text", "")
    doc_names = [d.get("original_name", "Document") for d in docs]

    if not demo_mode:
        prompt = f"""
Submitted Claim Intake Record:
- Policyholder Name: {claim.get('policyholder_name')}
- Policy Number: {claim.get('policy_number')}
- Vehicle Number: {claim.get('vehicle_number')}
- Vehicle Model: {claim.get('vehicle_model')}
- Accident Date: {claim.get('accident_date')}
- Accident Time: {claim.get('accident_time') or 'Not specified'}
- Accident Location: {claim.get('accident_location')}
- Claimed Amount (INR): {claim.get('claimed_amount')}
- Estimated Damage (INR): {claim.get('estimated_damage_amount') or claim.get('claimed_amount')}
- Damage Description: {claim.get('damage_description')}
- Uploaded File Names: {doc_names}

Extracted Document Text:
{combined_text if combined_text else '[No files attached or no text extracted]'}
"""
        result = generate_structured_json(SYSTEM_PROMPT, prompt, DocumentAgentOutput)
        if not result.detected_documents:
            result.detected_documents = doc_names
        return result

    # Deterministic Demo Mode (Explicitly labeled in workflow execution metadata)
    logger.info(f"[Demo Mode] Running Document Intelligence Agent for {claim.get('claim_id')}")
    regex_data = _extract_regex_fields(combined_text)

    validation_notes: List[str] = []
    missing_fields: List[str] = []

    policy_number = regex_data.get("policy_number") or claim.get("policy_number", "")
    vehicle_number = regex_data.get("vehicle_number") or claim.get("vehicle_number", "")
    accident_date = claim.get("accident_date", "")

    if regex_data.get("accident_date") and regex_data["accident_date"] != accident_date:
        validation_notes.append(
            f"Document accident date ({regex_data['accident_date']}) differs from intake form date ({accident_date})."
        )

    if regex_data.get("policy_number") and regex_data["policy_number"] != claim.get("policy_number"):
        validation_notes.append(
            f"Document policy number ({regex_data['policy_number']}) differs from intake ({claim.get('policy_number')})."
        )

    claimed_amt = float(claim.get("claimed_amount") or 0)
    est_amt = float(claim.get("estimated_damage_amount") or regex_data.get("extracted_amount") or claimed_amt)

    if not claim.get("accident_time"):
        missing_fields.append("accident_time")
    if not docs:
        missing_fields.append("supporting_documents")
        validation_notes.append("No digital PDF/image attachments uploaded; relying on intake metadata.")

    invoices = regex_data.get("invoice_numbers", [])
    if not invoices and claim.get("invoice_reference"):
        invoices = [claim["invoice_reference"]]

    confidence = 0.94 if docs and not validation_notes else (0.81 if docs else 0.68)

    return DocumentAgentOutput(
        policyholder_name=claim.get("policyholder_name", ""),
        policy_number=policy_number,
        vehicle_number=vehicle_number,
        vehicle_model=claim.get("vehicle_model", ""),
        accident_date=accident_date,
        accident_time=claim.get("accident_time", ""),
        accident_location=claim.get("accident_location", ""),
        estimated_damage_amount=est_amt,
        claimed_amount=claimed_amt,
        damage_description=claim.get("damage_description", ""),
        invoice_numbers=invoices,
        detected_documents=doc_names,
        missing_fields=missing_fields,
        validation_notes=validation_notes,
        confidence=confidence,
    )
