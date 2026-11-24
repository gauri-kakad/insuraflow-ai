from typing import Dict, Any, List, Optional
from models.schemas import (
    DocumentAgentOutput,
    PolicyAgentOutput,
    FraudAgentOutput,
    ClaimAssessmentOutput,
)
from services.gemini_service import generate_structured_json
from utils.logger import logger

SYSTEM_PROMPT = """
You are Agent 4: Claim Assessment & Decision-Support Agent for InsuraFlow AI.
Synthesize the structured outputs from Document Intelligence, Policy Verification, and Fraud Detection into an actionable assessment for a human claims officer.
CRITICAL RULES:
1. NEVER approve or reject a claim. Always set human_review_required = true.
2. Choose recommended_next_action strictly from:
   - 'Ready for Human Review'
   - 'Additional Documents Required'
   - 'Policy Verification Required'
   - 'Investigation Recommended'
3. Only calculate estimated_eligible_amount when policy_valid=true, coverage_applicable=true, risk_level != 'High', and no critical policy exclusions apply. Formula: min(claimed_amount, coverage_limit) - deductible (floored at 0). Otherwise set estimated_eligible_amount = null.
4. Clearly separate verified facts, missing documentation, and unresolved questions for the human reviewer.
"""


def run_assessment_agent(
    claim: Dict[str, Any],
    doc_out: DocumentAgentOutput,
    pol_out: PolicyAgentOutput,
    fraud_out: FraudAgentOutput,
    demo_mode: bool = False,
) -> ClaimAssessmentOutput:
    if not demo_mode:
        prompt = f"""
Claim ID: {claim.get('claim_id')}

1. Document Intelligence Output:
{doc_out.model_dump_json(indent=2)}

2. Policy Verification Output:
{pol_out.model_dump_json(indent=2)}

3. Fraud Detection Output:
{fraud_out.model_dump_json(indent=2)}

Produce the final ClaimAssessmentOutput for human officer review.
"""
        result = generate_structured_json(SYSTEM_PROMPT, prompt, ClaimAssessmentOutput)
        result.human_review_required = True
        return result

    # Deterministic Demo Mode
    logger.info(f"[Demo Mode] Running Claim Assessment Agent for {claim.get('claim_id')}")

    unresolved: List[str] = []
    for f in pol_out.policy_findings:
        unresolved.append(f)
    for note in doc_out.validation_notes:
        unresolved.append(note)
    for ind in fraud_out.indicators:
        unresolved.append(f"[{ind.severity}] {ind.type}: {ind.evidence}")

    # Determine recommended action
    if fraud_out.risk_level == "High":
        action = "Investigation Recommended"
    elif not pol_out.policy_found or not pol_out.policy_valid or not pol_out.coverage_applicable:
        action = "Policy Verification Required"
    elif pol_out.missing_documents:
        action = "Additional Documents Required"
    else:
        action = "Ready for Human Review"

    eligible_amount: Optional[float] = None
    if pol_out.policy_valid and pol_out.coverage_applicable and fraud_out.risk_level != "High":
        capped = min(doc_out.claimed_amount, pol_out.coverage_limit)
        eligible_amount = max(0.0, round(capped - pol_out.deductible, 2))

    pol_status_text = (
        f"Verified Active ({pol_out.coverage_type}, IDV INR {pol_out.coverage_limit:,.0f}, Deductible INR {pol_out.deductible:,.0f})"
        if pol_out.policy_valid and pol_out.coverage_applicable
        else f"Verification Issue ({'; '.join(pol_out.policy_findings) or 'Policy unverified'})"
    )

    summary = (
        f"Motor claim {claim.get('claim_id')} filed by {doc_out.policyholder_name} for vehicle {doc_out.vehicle_number} "
        f"({doc_out.vehicle_model}) reporting incident on {doc_out.accident_date} at {doc_out.accident_location}. "
        f"Claimed amount: INR {doc_out.claimed_amount:,.2f}."
    )

    explanation_parts = [
        f"Recommended next step: {action}.",
        f"Fraud & anomaly evaluation scored {fraud_out.risk_score}/100 ({fraud_out.risk_level} Risk).",
    ]
    if eligible_amount is not None:
        explanation_parts.append(
            f"Subject to human officer verification, preliminary policy math indicates an eligible estimate of INR {eligible_amount:,.2f} after INR {pol_out.deductible:,.2f} deductible."
        )
    else:
        explanation_parts.append(
            "Preliminary eligible payout is withheld pending resolution of policy validity or high-priority anomaly flags."
        )

    return ClaimAssessmentOutput(
        claim_summary=summary,
        policy_verification_status=pol_status_text,
        fraud_risk_level=fraud_out.risk_level,
        fraud_risk_score=fraud_out.risk_score,
        fraud_indicators=fraud_out.indicators,
        missing_documents=pol_out.missing_documents,
        unresolved_questions=unresolved,
        estimated_eligible_amount=eligible_amount,
        explanation=" ".join(explanation_parts),
        recommended_next_action=action,
        human_review_required=True,
    )
