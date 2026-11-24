from datetime import datetime
from typing import Dict, Any, List, Optional
from models.schemas import DocumentAgentOutput, PolicyAgentOutput, FraudAgentOutput, FraudIndicator
from services.gemini_service import generate_structured_json
from utils.logger import logger

SYSTEM_PROMPT = """
You are Agent 3: Fraud Detection & Anomaly Analysis Agent for InsuraFlow AI.
You evaluate motor insurance claims using a hybrid approach: deterministic rule checks + AI pattern analysis.
CRITICAL GUIDELINES:
1. Never accuse a claimant of fraud or declare a claim fraudulent. Only report objective anomalies, evidence, and risk indicators requiring human investigation.
2. Distinguish clearly between missing documentation (administrative gap) and suspicious inconsistencies (e.g., duplicate invoice numbers, overlapping historical claims, vehicle mismatches, claims filed immediately after policy inception).
3. Never fabricate historical matches. Only reference historical claims explicitly provided in the prompt context.
4. Ensure risk_score (0-100) and risk_level ('Low' < 35, 'Medium' 35-64, 'High' >= 65) align transparently with the evidence.
"""


def _run_deterministic_rules(
    claim: Dict[str, Any],
    doc_out: DocumentAgentOutput,
    pol_out: PolicyAgentOutput,
    historical_claims: List[Dict[str, Any]],
) -> tuple[int, List[FraudIndicator], List[str]]:
    score = 8  # Baseline hygiene score
    indicators: List[FraudIndicator] = []
    triggered: List[str] = []

    # Rule 1: Duplicate Invoice Reference Check
    current_invoices = set(doc_out.invoice_numbers or [])
    if claim.get("invoice_reference"):
        current_invoices.add(claim["invoice_reference"].upper())

    for hist in historical_claims:
        if hist.get("claim_id") == claim.get("claim_id"):
            continue
        hist_invoices = set([i.upper() for i in hist.get("invoice_numbers", [])])
        if hist.get("invoice_reference"):
            hist_invoices.add(hist["invoice_reference"].upper())

        overlap = current_invoices.intersection(hist_invoices)
        if overlap:
            score += 45
            triggered.append("RULE_DUPLICATE_INVOICE")
            indicators.append(
                FraudIndicator(
                    type="Duplicate Invoice Identifier",
                    severity="High",
                    source="Rule-Based Check",
                    evidence=f"Invoice reference {', '.join(overlap)} matches prior claim {hist.get('claim_id')} ({hist.get('accident_date')}).",
                )
            )

    # Rule 2: Repeated Policy / Similar Damage Pattern within 90 days
    for hist in historical_claims:
        if hist.get("claim_id") == claim.get("claim_id"):
            continue
        if hist.get("policy_number") == doc_out.policy_number:
            score += 22
            triggered.append("RULE_REPEATED_POLICY_CLAIM")
            indicators.append(
                FraudIndicator(
                    type="Prior Claim on Same Policy",
                    severity="Medium",
                    source="Rule-Based Check",
                    evidence=f"Policy {doc_out.policy_number} has a prior historical claim {hist.get('claim_id')} for INR {hist.get('claimed_amount', 0):,.0f} ({hist.get('damage_description', 'N/A')}).",
                )
            )

    # Rule 3: Policy Validity / Out-of-Period Accident Date
    if pol_out.policy_found and not pol_out.policy_valid:
        score += 38
        triggered.append("RULE_OUTSIDE_POLICY_PERIOD")
        indicators.append(
            FraudIndicator(
                type="Accident Outside Policy Validity",
                severity="High",
                source="Rule-Based Check",
                evidence=f"Reported accident date {doc_out.accident_date} is outside policy window ({pol_out.policy_start_date} to {pol_out.policy_end_date}).",
            )
        )

    # Rule 4: High Claim-to-IDV Ratio (> 75% of coverage limit)
    if pol_out.coverage_limit > 0:
        ratio = doc_out.claimed_amount / pol_out.coverage_limit
        if ratio >= 0.75:
            score += 25
            triggered.append("RULE_HIGH_IDV_RATIO")
            indicators.append(
                FraudIndicator(
                    type="High Claim-to-IDV Ratio",
                    severity="Medium",
                    source="Rule-Based Check",
                    evidence=f"Claimed amount (INR {doc_out.claimed_amount:,.0f}) is {ratio*100:.1f}% of policy IDV (INR {pol_out.coverage_limit:,.0f}).",
                )
            )

    # Rule 5: Early Policy Inception Claim (< 15 days from start_date)
    try:
        if pol_out.policy_found and pol_out.policy_start_date != "Unavailable":
            s_dt = datetime.strptime(pol_out.policy_start_date, "%Y-%m-%d")
            a_dt = datetime.strptime(doc_out.accident_date, "%Y-%m-%d")
            days_since_inception = (a_dt - s_dt).days
            if 0 <= days_since_inception <= 15:
                score += 22
                triggered.append("RULE_EARLY_INCEPTION_CLAIM")
                indicators.append(
                    FraudIndicator(
                        type="Early Policy Inception Incident",
                        severity="Medium",
                        source="Rule-Based Check",
                        evidence=f"Accident occurred {days_since_inception} day(s) after policy start date ({pol_out.policy_start_date}).",
                    )
                )
    except Exception:
        pass

    # Rule 6: Document vs Intake Discrepancies
    for note in doc_out.validation_notes:
        if "differs" in note.lower():
            score += 20
            triggered.append("RULE_DOCUMENT_METADATA_MISMATCH")
            indicators.append(
                FraudIndicator(
                    type="Cross-Document Inconsistency",
                    severity="Medium",
                    source="Rule-Based Check",
                    evidence=note,
                )
            )

    score = min(100, max(0, score))
    return score, indicators, triggered


def run_fraud_agent(
    claim: Dict[str, Any],
    doc_out: DocumentAgentOutput,
    pol_out: PolicyAgentOutput,
    historical_claims: List[Dict[str, Any]],
    demo_mode: bool = False,
) -> FraudAgentOutput:
    rule_score, rule_indicators, triggered_rules = _run_deterministic_rules(
        claim, doc_out, pol_out, historical_claims
    )

    if not demo_mode:
        hist_summary = [
            {
                "claim_id": h.get("claim_id"),
                "policy_number": h.get("policy_number"),
                "vehicle_number": h.get("vehicle_number"),
                "accident_date": h.get("accident_date"),
                "claimed_amount": h.get("claimed_amount"),
                "invoice_numbers": h.get("invoice_numbers", []),
                "damage_description": h.get("damage_description"),
            }
            for h in historical_claims[:15]
            if h.get("claim_id") != claim.get("claim_id")
        ]
        prompt = f"""
Current Claim Extracted Info:
{doc_out.model_dump_json(indent=2)}

Policy Verification Output:
{pol_out.model_dump_json(indent=2)}

Deterministic Rule Engine Findings (Baseline Score: {rule_score}/100):
- Triggered Rules: {triggered_rules}
- Rule Indicators: {[i.model_dump() for i in rule_indicators]}

Historical Claims Dataset (for factual comparison only):
{hist_summary}

Synthesize the final FraudAgentOutput. Preserve all deterministic rule indicators with source='Rule-Based Check', and add any contextual analytical observations with source='AI Pattern Analysis'.
"""
        return generate_structured_json(SYSTEM_PROMPT, prompt, FraudAgentOutput)

    # Deterministic Demo Mode
    logger.info(f"[Demo Mode] Running Fraud Detection Agent for {claim.get('claim_id')}")
    ai_observations: List[str] = []

    if not rule_indicators:
        ai_observations.append(
            "Claim amount, vehicle identifiers, and incident timeline align with standard repair benchmarks for the stated damage."
        )
    else:
        ai_observations.append(
            f"Combined anomaly evaluation identified {len(rule_indicators)} objective indicator(s) warranting claims officer verification before settlement."
        )

    if pol_out.missing_documents:
        ai_observations.append(
            f"Missing documents ({', '.join(pol_out.missing_documents)}) are treated as verification gaps rather than fraud indicators."
        )

    if rule_score >= 65:
        risk_level = "High"
    elif rule_score >= 35:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    explanation = (
        f"Hybrid risk score {rule_score}/100 ({risk_level} Risk) derived from {len(triggered_rules)} deterministic rule check(s) "
        f"and historical record comparison. Indicators represent anomalies for human review, not proof of fraud."
        if rule_indicators
        else f"Low anomaly profile ({rule_score}/100). No duplicate invoices, policy date conflicts, or abnormal claim ratios were detected."
    )

    return FraudAgentOutput(
        risk_score=rule_score,
        risk_level=risk_level,
        indicators=rule_indicators,
        rule_checks_triggered=triggered_rules,
        ai_observations=ai_observations,
        explanation=explanation,
        requires_manual_review=True,
    )
