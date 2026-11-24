import time
import uuid
from datetime import datetime, timezone
from typing import TypedDict, Optional, Dict, Any, List
from langgraph.graph import StateGraph, START, END

from database import get_database
from config import settings
from utils.logger import logger
from models.schemas import (
    DocumentAgentOutput,
    PolicyAgentOutput,
    FraudAgentOutput,
    ClaimAssessmentOutput,
)
from agents.document_agent import run_document_agent
from agents.policy_agent import run_policy_agent
from agents.fraud_agent import run_fraud_agent
from agents.assessment_agent import run_assessment_agent


class ClaimWorkflowState(TypedDict):
    execution_id: str
    claim_id: str
    demo_mode: bool
    claim_data: Dict[str, Any]
    policy_data: Optional[Dict[str, Any]]
    historical_claims: List[Dict[str, Any]]
    document_result: Optional[Dict[str, Any]]
    policy_result: Optional[Dict[str, Any]]
    fraud_result: Optional[Dict[str, Any]]
    assessment_result: Optional[Dict[str, Any]]
    stages: Dict[str, Dict[str, Any]]
    logs: List[str]
    error: Optional[str]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _persist_execution_state(state: ClaimWorkflowState, overall_status: str = "running") -> None:
    db = get_database()
    stage_list = [
        state["stages"]["document_agent"],
        state["stages"]["policy_agent"],
        state["stages"]["fraud_agent"],
        state["stages"]["assessment_agent"],
    ]
    db.agent_executions.update_one(
        {"execution_id": state["execution_id"]},
        {
            "$set": {
                "execution_id": state["execution_id"],
                "claim_id": state["claim_id"],
                "demo_mode": state["demo_mode"],
                "model_used": "Deterministic Demo Engine" if state["demo_mode"] else settings.GEMINI_MODEL,
                "status": overall_status,
                "stages": stage_list,
                "logs": state["logs"],
                "error": state.get("error"),
                "updated_at": _now_iso(),
            }
        },
        upsert=True,
    )


def document_node(state: ClaimWorkflowState) -> ClaimWorkflowState:
    if state.get("error"):
        return state

    stage = state["stages"]["document_agent"]
    stage["status"] = "running"
    stage["started_at"] = _now_iso()
    state["logs"].append(f"[{_now_iso()}] Starting Document Intelligence Agent...")
    _persist_execution_state(state, "running")

    t0 = time.perf_counter()
    try:
        output = run_document_agent(state["claim_data"], demo_mode=state["demo_mode"])
        elapsed = int((time.perf_counter() - t0) * 1000)
        out_dict = output.model_dump()

        findings = [
            f"Extracted policy {output.policy_number} for vehicle {output.vehicle_number}",
            f"Claimed amount: INR {output.claimed_amount:,.2f} (Confidence: {int(output.confidence * 100)}%)",
        ]
        if output.validation_notes:
            findings.extend(output.validation_notes)

        stage["status"] = "completed"
        stage["completed_at"] = _now_iso()
        stage["duration_ms"] = elapsed
        stage["key_findings"] = findings
        stage["output"] = out_dict

        state["document_result"] = out_dict
        state["logs"].append(f"[{_now_iso()}] Document Intelligence Agent completed in {elapsed}ms.")
    except Exception as exc:
        elapsed = int((time.perf_counter() - t0) * 1000)
        stage["status"] = "failed"
        stage["completed_at"] = _now_iso()
        stage["duration_ms"] = elapsed
        stage["error"] = str(exc)
        state["error"] = f"Document Intelligence Agent failed: {str(exc)}"
        state["logs"].append(f"[{_now_iso()}] ERROR in Document Agent: {str(exc)}")

    _persist_execution_state(state, "failed" if state.get("error") else "running")
    return state


def policy_node(state: ClaimWorkflowState) -> ClaimWorkflowState:
    if state.get("error") or not state.get("document_result"):
        return state

    stage = state["stages"]["policy_agent"]
    stage["status"] = "running"
    stage["started_at"] = _now_iso()
    state["logs"].append(f"[{_now_iso()}] Starting Policy Verification Agent...")
    _persist_execution_state(state, "running")

    t0 = time.perf_counter()
    try:
        doc_out = DocumentAgentOutput.model_validate(state["document_result"])
        # Re-query policy if extracted policy_number differs from initial lookup
        db = get_database()
        policy_rec = db.policies.find_one({"policy_number": doc_out.policy_number}, {"_id": 0}) or state.get("policy_data")

        output = run_policy_agent(doc_out, policy_rec, demo_mode=state["demo_mode"])
        elapsed = int((time.perf_counter() - t0) * 1000)
        out_dict = output.model_dump()

        findings = [
            f"Policy Found: {'Yes' if output.policy_found else 'No'} | Valid on Incident Date: {'Yes' if output.policy_valid else 'No'}",
            f"Coverage: {output.coverage_type} | Limit: INR {output.coverage_limit:,.0f} | Deductible: INR {output.deductible:,.0f}",
        ]
        if output.missing_documents:
            findings.append(f"Missing Docs: {', '.join(output.missing_documents)}")
        findings.extend(output.policy_findings)

        stage["status"] = "completed"
        stage["completed_at"] = _now_iso()
        stage["duration_ms"] = elapsed
        stage["key_findings"] = findings
        stage["output"] = out_dict

        state["policy_result"] = out_dict
        state["logs"].append(f"[{_now_iso()}] Policy Verification Agent completed in {elapsed}ms.")
    except Exception as exc:
        elapsed = int((time.perf_counter() - t0) * 1000)
        stage["status"] = "failed"
        stage["completed_at"] = _now_iso()
        stage["duration_ms"] = elapsed
        stage["error"] = str(exc)
        state["error"] = f"Policy Verification Agent failed: {str(exc)}"
        state["logs"].append(f"[{_now_iso()}] ERROR in Policy Agent: {str(exc)}")

    _persist_execution_state(state, "failed" if state.get("error") else "running")
    return state


def fraud_node(state: ClaimWorkflowState) -> ClaimWorkflowState:
    if state.get("error") or not state.get("policy_result"):
        return state

    stage = state["stages"]["fraud_agent"]
    stage["status"] = "running"
    stage["started_at"] = _now_iso()
    state["logs"].append(f"[{_now_iso()}] Starting Fraud Detection Agent...")
    _persist_execution_state(state, "running")

    t0 = time.perf_counter()
    try:
        doc_out = DocumentAgentOutput.model_validate(state["document_result"])
        pol_out = PolicyAgentOutput.model_validate(state["policy_result"])

        output = run_fraud_agent(
            state["claim_data"],
            doc_out,
            pol_out,
            state.get("historical_claims", []),
            demo_mode=state["demo_mode"],
        )
        elapsed = int((time.perf_counter() - t0) * 1000)
        out_dict = output.model_dump()

        findings = [
            f"Risk Score: {output.risk_score}/100 ({output.risk_level} Risk)",
            f"Indicators Detected: {len(output.indicators)}",
        ]
        for ind in output.indicators:
            findings.append(f"[{ind.severity}] {ind.type}: {ind.evidence}")

        stage["status"] = "completed"
        stage["completed_at"] = _now_iso()
        stage["duration_ms"] = elapsed
        stage["key_findings"] = findings
        stage["output"] = out_dict

        state["fraud_result"] = out_dict
        state["logs"].append(f"[{_now_iso()}] Fraud Detection Agent completed in {elapsed}ms.")
    except Exception as exc:
        elapsed = int((time.perf_counter() - t0) * 1000)
        stage["status"] = "failed"
        stage["completed_at"] = _now_iso()
        stage["duration_ms"] = elapsed
        stage["error"] = str(exc)
        state["error"] = f"Fraud Detection Agent failed: {str(exc)}"
        state["logs"].append(f"[{_now_iso()}] ERROR in Fraud Agent: {str(exc)}")

    _persist_execution_state(state, "failed" if state.get("error") else "running")
    return state


def assessment_node(state: ClaimWorkflowState) -> ClaimWorkflowState:
    if state.get("error") or not state.get("fraud_result"):
        return state

    stage = state["stages"]["assessment_agent"]
    stage["status"] = "running"
    stage["started_at"] = _now_iso()
    state["logs"].append(f"[{_now_iso()}] Starting Claim Assessment Agent...")
    _persist_execution_state(state, "running")

    t0 = time.perf_counter()
    try:
        doc_out = DocumentAgentOutput.model_validate(state["document_result"])
        pol_out = PolicyAgentOutput.model_validate(state["policy_result"])
        fraud_out = FraudAgentOutput.model_validate(state["fraud_result"])

        output = run_assessment_agent(
            state["claim_data"],
            doc_out,
            pol_out,
            fraud_out,
            demo_mode=state["demo_mode"],
        )
        elapsed = int((time.perf_counter() - t0) * 1000)
        out_dict = output.model_dump()

        findings = [
            f"Recommended Action: {output.recommended_next_action}",
            f"Human Review Required: Yes (Mandatory Policy)",
        ]
        if output.estimated_eligible_amount is not None:
            findings.append(f"Preliminary Eligible Estimate: INR {output.estimated_eligible_amount:,.2f}")

        stage["status"] = "completed"
        stage["completed_at"] = _now_iso()
        stage["duration_ms"] = elapsed
        stage["key_findings"] = findings
        stage["output"] = out_dict

        state["assessment_result"] = out_dict
        state["logs"].append(f"[{_now_iso()}] Claim Assessment Agent completed in {elapsed}ms.")
    except Exception as exc:
        elapsed = int((time.perf_counter() - t0) * 1000)
        stage["status"] = "failed"
        stage["completed_at"] = _now_iso()
        stage["duration_ms"] = elapsed
        stage["error"] = str(exc)
        state["error"] = f"Claim Assessment Agent failed: {str(exc)}"
        state["logs"].append(f"[{_now_iso()}] ERROR in Assessment Agent: {str(exc)}")

    _persist_execution_state(state, "failed" if state.get("error") else "completed")
    return state


def build_claim_graph():
    workflow = StateGraph(ClaimWorkflowState)
    workflow.add_node("document_agent", document_node)
    workflow.add_node("policy_agent", policy_node)
    workflow.add_node("fraud_agent", fraud_node)
    workflow.add_node("assessment_agent", assessment_node)

    workflow.add_edge(START, "document_agent")
    workflow.add_edge("document_agent", "policy_agent")
    workflow.add_edge("policy_agent", "fraud_agent")
    workflow.add_edge("fraud_agent", "assessment_agent")
    workflow.add_edge("assessment_agent", END)

    return workflow.compile()


compiled_claim_graph = build_claim_graph()


def execute_claim_workflow(claim_id: str, demo_mode: bool = False, triggered_by: str = "System") -> Dict[str, Any]:
    db = get_database()
    claim = db.claims.find_one({"claim_id": claim_id}, {"_id": 0})
    if not claim:
        raise ValueError(f"Claim '{claim_id}' not found.")

    policy = db.policies.find_one({"policy_number": claim.get("policy_number")}, {"_id": 0})
    historical_claims = list(
        db.claims.find({"claim_id": {"$ne": claim_id}}, {"_id": 0}).limit(50)
    )

    execution_id = f"EXEC-{uuid.uuid4().hex[:10].upper()}"
    started_at = _now_iso()
    t_total = time.perf_counter()

    initial_state: ClaimWorkflowState = {
        "execution_id": execution_id,
        "claim_id": claim_id,
        "demo_mode": demo_mode,
        "claim_data": claim,
        "policy_data": policy,
        "historical_claims": historical_claims,
        "document_result": None,
        "policy_result": None,
        "fraud_result": None,
        "assessment_result": None,
        "stages": {
            "document_agent": {
                "agent_id": "document_agent",
                "agent_name": "Document Intelligence Agent",
                "status": "pending",
                "started_at": None,
                "completed_at": None,
                "duration_ms": None,
                "key_findings": [],
                "output": None,
                "error": None,
            },
            "policy_agent": {
                "agent_id": "policy_agent",
                "agent_name": "Policy Verification Agent",
                "status": "pending",
                "started_at": None,
                "completed_at": None,
                "duration_ms": None,
                "key_findings": [],
                "output": None,
                "error": None,
            },
            "fraud_agent": {
                "agent_id": "fraud_agent",
                "agent_name": "Fraud Detection Agent",
                "status": "pending",
                "started_at": None,
                "completed_at": None,
                "duration_ms": None,
                "key_findings": [],
                "output": None,
                "error": None,
            },
            "assessment_agent": {
                "agent_id": "assessment_agent",
                "agent_name": "Claim Assessment Agent",
                "status": "pending",
                "started_at": None,
                "completed_at": None,
                "duration_ms": None,
                "key_findings": [],
                "output": None,
                "error": None,
            },
        },
        "logs": [
            f"[{started_at}] Workflow {execution_id} initialized by {triggered_by} "
            f"({'Deterministic Demo Mode' if demo_mode else f'Live Gemini ({settings.GEMINI_MODEL})'})."
        ],
        "error": None,
    }

    db.claims.update_one(
        {"claim_id": claim_id},
        {"$set": {"status": "Processing", "latest_execution_id": execution_id}},
    )
    db.agent_executions.insert_one({
        "execution_id": execution_id,
        "claim_id": claim_id,
        "demo_mode": demo_mode,
        "model_used": "Deterministic Demo Engine" if demo_mode else settings.GEMINI_MODEL,
        "status": "running",
        "started_at": started_at,
        "stages": list(initial_state["stages"].values()),
        "logs": initial_state["logs"],
        "error": None,
    })

    final_state = compiled_claim_graph.invoke(initial_state)
    total_ms = int((time.perf_counter() - t_total) * 1000)

    if final_state.get("error"):
        db.claims.update_one(
            {"claim_id": claim_id},
            {"$set": {"status": "Processing Failed", "processing_time_ms": total_ms}},
        )
        db.audit_logs.insert_one({
            "audit_id": f"AUD-{uuid.uuid4().hex[:8].upper()}",
            "claim_id": claim_id,
            "actor": triggered_by,
            "actor_type": "system",
            "action": "AI Workflow Failed",
            "details": final_state["error"],
            "timestamp": _now_iso(),
        })
        return {
            "execution_id": execution_id,
            "status": "failed",
            "error": final_state["error"],
        }

    assessment = final_state["assessment_result"]
    fraud = final_state["fraud_result"]
    doc_res = final_state["document_result"]
    pol_res = final_state["policy_result"]

    assessment_doc = {
        "claim_id": claim_id,
        "execution_id": execution_id,
        "demo_mode": demo_mode,
        "model_used": "Deterministic Demo Engine" if demo_mode else settings.GEMINI_MODEL,
        "document_intelligence": doc_res,
        "policy_verification": pol_res,
        "fraud_analysis": fraud,
        "final_assessment": assessment,
        "processing_time_ms": total_ms,
        "assessed_at": _now_iso(),
    }

    db.assessments.update_one(
        {"claim_id": claim_id},
        {"$set": assessment_doc},
        upsert=True,
    )

    new_claim_status = (
        "Under Investigation"
        if assessment["recommended_next_action"] == "Investigation Recommended"
        else (
            "Additional Docs Required"
            if assessment["recommended_next_action"] == "Additional Documents Required"
            else "Pending Human Review"
        )
    )

    db.claims.update_one(
        {"claim_id": claim_id},
        {
            "$set": {
                "status": new_claim_status,
                "risk_level": fraud["risk_level"],
                "risk_score": fraud["risk_score"],
                "recommended_next_action": assessment["recommended_next_action"],
                "estimated_eligible_amount": assessment.get("estimated_eligible_amount"),
                "invoice_numbers": doc_res.get("invoice_numbers", []),
                "processing_time_ms": total_ms,
                "last_processed_at": _now_iso(),
            }
        },
    )

    db.audit_logs.insert_one({
        "audit_id": f"AUD-{uuid.uuid4().hex[:8].upper()}",
        "claim_id": claim_id,
        "actor": f"LangGraph Orchestrator ({'Demo Mode' if demo_mode else settings.GEMINI_MODEL})",
        "actor_type": "ai_workflow",
        "action": "Multi-Agent Assessment Completed",
        "details": (
            f"Risk Score: {fraud['risk_score']}/100 ({fraud['risk_level']}). "
            f"Recommendation: {assessment['recommended_next_action']}. Queued for mandatory human review."
        ),
        "timestamp": _now_iso(),
    })

    logger.info(f"Completed LangGraph workflow {execution_id} for {claim_id} in {total_ms}ms")
    return {
        "execution_id": execution_id,
        "status": "completed",
        "processing_time_ms": total_ms,
        "assessment": assessment_doc,
    }
