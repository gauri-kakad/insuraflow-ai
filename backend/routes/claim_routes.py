import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
    BackgroundTasks,
    Query,
)
from fastapi.responses import Response

from database import get_database
from config import settings
from models.schemas import ProcessTriggerRequest, HumanReviewRequest
from utils.security import get_current_user, validate_and_save_upload
from workflows.graph import execute_claim_workflow
from services.pdf_report import generate_claim_assessment_pdf
from utils.logger import logger

router = APIRouter(prefix="/api", tags=["Claims & Multi-Agent Processing"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.post("/claims", status_code=status.HTTP_201_CREATED)
async def create_claim(
    policyholder_name: str = Form(...),
    policyholder_email: str = Form(""),
    policyholder_phone: str = Form(""),
    policy_number: str = Form(...),
    vehicle_number: str = Form(...),
    vehicle_model: str = Form(...),
    accident_date: str = Form(...),
    accident_time: str = Form(""),
    accident_location: str = Form(...),
    claimed_amount: float = Form(...),
    estimated_damage_amount: Optional[float] = Form(None),
    damage_description: str = Form(...),
    supporting_documents: List[UploadFile] = File(default=[]),
    policy_documents: List[UploadFile] = File(default=[]),
    current_user: dict = Depends(get_current_user),
):
    if claimed_amount <= 0:
        raise HTTPException(status_code=400, detail="Claimed amount must be greater than zero.")

    claim_id = f"CLM-2026-{uuid.uuid4().hex[:4].upper()}"
    saved_docs = []

    for f in supporting_documents:
        if f and f.filename:
            meta = await validate_and_save_upload(f, claim_id)
            meta["doc_category"] = "supporting_document"
            saved_docs.append(meta)

    for pf in policy_documents:
        if pf and pf.filename:
            meta = await validate_and_save_upload(pf, claim_id)
            meta["doc_category"] = "policy_document"
            saved_docs.append(meta)

    now = _now_iso()
    claim_doc = {
        "claim_id": claim_id,
        "policyholder_name": policyholder_name.strip(),
        "policyholder_email": policyholder_email.strip(),
        "policyholder_phone": policyholder_phone.strip(),
        "policy_number": policy_number.strip().upper(),
        "vehicle_number": vehicle_number.strip().upper().replace(" ", ""),
        "vehicle_model": vehicle_model.strip(),
        "accident_date": accident_date.strip(),
        "accident_time": accident_time.strip(),
        "accident_location": accident_location.strip(),
        "claimed_amount": float(claimed_amount),
        "estimated_damage_amount": float(estimated_damage_amount) if estimated_damage_amount else float(claimed_amount),
        "damage_description": damage_description.strip(),
        "documents": saved_docs,
        "status": "Submitted",
        "risk_level": "Pending",
        "risk_score": None,
        "submitted_by": current_user["name"],
        "submitted_at": now,
    }

    db = get_database()
    db.claims.insert_one(claim_doc)
    db.audit_logs.insert_one({
        "audit_id": f"AUD-{uuid.uuid4().hex[:8].upper()}",
        "claim_id": claim_id,
        "actor": current_user["name"],
        "actor_type": "officer",
        "action": "Claim Submitted",
        "details": f"Claim {claim_id} created for policy {claim_doc['policy_number']} with {len(saved_docs)} uploaded file(s).",
        "timestamp": now,
    })

    claim_doc.pop("_id", None)
    return {"message": "Claim submitted successfully.", "claim": claim_doc}


@router.get("/claims")
def list_claims(
    search: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    db = get_database()
    query: dict = {}

    if search:
        s = search.strip()
        query["$or"] = [
            {"claim_id": {"$regex": s, "$options": "i"}},
            {"policy_number": {"$regex": s, "$options": "i"}},
            {"policyholder_name": {"$regex": s, "$options": "i"}},
            {"vehicle_number": {"$regex": s, "$options": "i"}},
        ]
    if risk_level and risk_level != "All":
        query["risk_level"] = risk_level
    if status_filter and status_filter != "All":
        query["status"] = status_filter
    if date_from or date_to:
        date_q = {}
        if date_from:
            date_q["$gte"] = date_from
        if date_to:
            date_q["$lte"] = date_to + "T23:59:59"
        query["submitted_at"] = date_q

    claims = list(db.claims.find(query, {"_id": 0}).sort("submitted_at", -1))
    return {"claims": claims, "total": len(claims)}


@router.get("/claims/{claim_id}")
def get_claim(claim_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    claim = db.claims.find_one({"claim_id": claim_id}, {"_id": 0})
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim '{claim_id}' not found.")

    policy = db.policies.find_one({"policy_number": claim.get("policy_number")}, {"_id": 0})
    assessment = db.assessments.find_one({"claim_id": claim_id}, {"_id": 0})
    executions = list(
        db.agent_executions.find({"claim_id": claim_id}, {"_id": 0}).sort("started_at", -1)
    )
    audit_logs = list(
        db.audit_logs.find({"claim_id": claim_id}, {"_id": 0}).sort("timestamp", -1)
    )

    return {
        "claim": claim,
        "policy": policy,
        "assessment": assessment,
        "executions": executions,
        "audit_logs": audit_logs,
    }


@router.delete("/claims/{claim_id}")
def delete_claim(claim_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    res = db.claims.delete_one({"claim_id": claim_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail=f"Claim '{claim_id}' not found.")

    db.assessments.delete_many({"claim_id": claim_id})
    db.agent_executions.delete_many({"claim_id": claim_id})
    db.audit_logs.insert_one({
        "audit_id": f"AUD-{uuid.uuid4().hex[:8].upper()}",
        "claim_id": claim_id,
        "actor": current_user["name"],
        "actor_type": "officer",
        "action": "Claim Deleted",
        "details": f"Claim record {claim_id} removed from active queue.",
        "timestamp": _now_iso(),
    })
    return {"message": f"Claim {claim_id} deleted."}


@router.post("/claims/{claim_id}/process")
def process_claim(
    claim_id: str,
    background_tasks: BackgroundTasks,
    payload: Optional[ProcessTriggerRequest] = None,
    current_user: dict = Depends(get_current_user),
):
    db = get_database()
    claim = db.claims.find_one({"claim_id": claim_id}, {"_id": 0})
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim '{claim_id}' not found.")

    requested_demo = payload.use_demo_mode if payload and payload.use_demo_mode is not None else (not settings.has_live_gemini)

    if not requested_demo and not settings.has_live_gemini:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Live Google Gemini API credentials (GEMINI_API_KEY) are not configured on the server. Enable Deterministic Demo Mode or configure GEMINI_API_KEY in backend/.env.",
        )

    # Mark claim immediately as queued/processing so frontend polling sees live state transitions
    db.claims.update_one({"claim_id": claim_id}, {"$set": {"status": "Processing"}})
    background_tasks.add_task(
        execute_claim_workflow,
        claim_id=claim_id,
        demo_mode=requested_demo,
        triggered_by=current_user["name"],
    )

    return {
        "message": "LangGraph multi-agent workflow started.",
        "claim_id": claim_id,
        "demo_mode": requested_demo,
        "engine": "Deterministic Demo Engine" if requested_demo else settings.GEMINI_MODEL,
    }


@router.get("/claims/{claim_id}/status")
def get_processing_status(claim_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    claim = db.claims.find_one({"claim_id": claim_id}, {"_id": 0})
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim '{claim_id}' not found.")

    execution = db.agent_executions.find_one(
        {"claim_id": claim_id},
        {"_id": 0},
        sort=[("started_at", -1), ("updated_at", -1)],
    )

    return {
        "claim_id": claim_id,
        "claim_status": claim.get("status"),
        "execution": execution,
    }


@router.get("/claims/{claim_id}/assessment")
def get_claim_assessment(claim_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    assessment = db.assessments.find_one({"claim_id": claim_id}, {"_id": 0})
    if not assessment:
        raise HTTPException(
            status_code=404,
            detail="No AI assessment available yet. Trigger multi-agent processing first.",
        )
    return assessment


@router.post("/claims/{claim_id}/review")
def submit_human_review(
    claim_id: str,
    payload: HumanReviewRequest,
    current_user: dict = Depends(get_current_user),
):
    db = get_database()
    claim = db.claims.find_one({"claim_id": claim_id}, {"_id": 0})
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim '{claim_id}' not found.")

    status_map = {
        "Mark Reviewed": "Reviewed",
        "Request Additional Documents": "Additional Docs Required",
        "Mark Under Investigation": "Under Investigation",
        "Approve Payout Recommendation": "Approved by Officer",
        "Reject Claim": "Rejected by Officer",
    }
    new_status = status_map[payload.action]
    now = _now_iso()

    review_record = {
        "decision": payload.action,
        "status_applied": new_status,
        "notes": payload.notes.strip(),
        "approved_amount": payload.approved_amount,
        "requested_documents": payload.requested_documents,
        "reviewer_id": current_user["user_id"],
        "reviewer_name": current_user["name"],
        "reviewer_role": current_user["role"],
        "reviewed_at": now,
    }

    db.claims.update_one(
        {"claim_id": claim_id},
        {
            "$set": {
                "status": new_status,
                "human_review": review_record,
                "updated_at": now,
            }
        },
    )

    detail_msg = f"Officer Action: {payload.action} -> Status '{new_status}'. Notes: {payload.notes.strip()}"
    if payload.approved_amount is not None:
        detail_msg += f" | Officer Approved Amount: INR {payload.approved_amount:,.2f}"

    db.audit_logs.insert_one({
        "audit_id": f"AUD-{uuid.uuid4().hex[:8].upper()}",
        "claim_id": claim_id,
        "actor": f"{current_user['name']} ({current_user['role']})",
        "actor_type": "officer",
        "action": payload.action,
        "details": detail_msg,
        "timestamp": now,
    })

    return {"message": "Human review decision recorded.", "status": new_status, "human_review": review_record}


@router.get("/claims/{claim_id}/audit")
def get_claim_audit(claim_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    logs = list(db.audit_logs.find({"claim_id": claim_id}, {"_id": 0}).sort("timestamp", -1))
    return {"claim_id": claim_id, "audit_logs": logs}


@router.get("/claims/{claim_id}/report")
def download_claim_report(claim_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    claim = db.claims.find_one({"claim_id": claim_id}, {"_id": 0})
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim '{claim_id}' not found.")

    assessment = db.assessments.find_one({"claim_id": claim_id}, {"_id": 0})
    audit_logs = list(db.audit_logs.find({"claim_id": claim_id}, {"_id": 0}).sort("timestamp", -1))

    pdf_bytes = generate_claim_assessment_pdf(claim, assessment, audit_logs)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="InsuraFlow_Assessment_{claim_id}.pdf"'
        },
    )


@router.get("/analytics/dashboard")
def get_dashboard_analytics(current_user: dict = Depends(get_current_user)):
    db = get_database()
    claims = list(db.claims.find({}, {"_id": 0}))
    assessments = list(db.assessments.find({}, {"_id": 0}))
    recent_activity = list(db.audit_logs.find({}, {"_id": 0}).sort("timestamp", -1).limit(10))

    total_claims = len(claims)
    pending_claims = sum(
        1 for c in claims if c.get("status") in {"Submitted", "Processing", "Additional Docs Required"}
    )
    human_review_claims = sum(
        1 for c in claims if c.get("status") in {"Pending Human Review", "Under Investigation", "Additional Docs Required"}
    )
    high_risk_claims = sum(1 for c in claims if c.get("risk_level") == "High")
    investigation_claims = sum(1 for c in claims if c.get("status") == "Under Investigation")

    proc_times = [c["processing_time_ms"] for c in claims if isinstance(c.get("processing_time_ms"), (int, float))]
    avg_processing_ms = int(sum(proc_times) / len(proc_times)) if proc_times else 0

    # Risk Distribution
    risk_counts = {"Low": 0, "Medium": 0, "High": 0, "Pending": 0}
    for c in claims:
        rl = c.get("risk_level") or "Pending"
        risk_counts[rl] = risk_counts.get(rl, 0) + 1

    risk_distribution = [
        {"name": "Low Risk", "value": risk_counts["Low"], "color": "#10B981"},
        {"name": "Medium Risk", "value": risk_counts["Medium"], "color": "#F59E0B"},
        {"name": "High Risk", "value": risk_counts["High"], "color": "#EF4444"},
    ]
    if risk_counts["Pending"] > 0:
        risk_distribution.append({"name": "Unprocessed", "value": risk_counts["Pending"], "color": "#94A3B8"})

    # Processing Trend grouped by submission date
    trend_map: dict = {}
    for c in claims:
        day = (c.get("submitted_at") or "2026-11-20")[:10]
        if day not in trend_map:
            trend_map[day] = {"date": day, "claims": 0, "high_risk": 0, "avg_ms": []}
        trend_map[day]["claims"] += 1
        if c.get("risk_level") == "High":
            trend_map[day]["high_risk"] += 1
        if c.get("processing_time_ms"):
            trend_map[day]["avg_ms"].append(c["processing_time_ms"])

    processing_trend = []
    for day in sorted(trend_map.keys()):
        item = trend_map[day]
        avg_d = int(sum(item["avg_ms"]) / len(item["avg_ms"])) if item["avg_ms"] else 0
        processing_trend.append({
            "date": day,
            "claims": item["claims"],
            "high_risk": item["high_risk"],
            "avg_processing_sec": round(avg_d / 1000, 2),
        })

    # Anomaly Category Breakdown from Assessments
    anomaly_counts: dict = {}
    for a in assessments:
        for ind in a.get("fraud_analysis", {}).get("indicators", []):
            itype = ind.get("type", "Other Anomaly")
            anomaly_counts[itype] = anomaly_counts.get(itype, 0) + 1

    anomaly_categories = [
        {"category": k, "count": v}
        for k, v in sorted(anomaly_counts.items(), key=lambda x: x[1], reverse=True)
    ]

    recent_claims = sorted(claims, key=lambda x: x.get("submitted_at", ""), reverse=True)[:6]

    return {
        "kpis": {
            "total_claims": total_claims,
            "pending_claims": pending_claims,
            "human_review_required": human_review_claims,
            "high_risk_claims": high_risk_claims,
            "investigation_claims": investigation_claims,
            "avg_processing_ms": avg_processing_ms,
        },
        "risk_distribution": risk_distribution,
        "processing_trend": processing_trend,
        "anomaly_categories": anomaly_categories,
        "recent_claims": recent_claims,
        "recent_activity": recent_activity,
    }
