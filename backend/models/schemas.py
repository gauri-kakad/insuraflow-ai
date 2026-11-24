from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


# ==========================================
# Auth Schemas
# ==========================================
class LoginRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=4)


class UserResponse(BaseModel):
    user_id: str
    name: str
    email: str
    role: str
    department: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ==========================================
# Multi-Agent Structured Outputs
# ==========================================
class DocumentAgentOutput(BaseModel):
    policyholder_name: str = ""
    policy_number: str = ""
    vehicle_number: str = ""
    vehicle_model: str = ""
    accident_date: str = ""
    accident_time: str = ""
    accident_location: str = ""
    estimated_damage_amount: float = 0.0
    claimed_amount: float = 0.0
    damage_description: str = ""
    invoice_numbers: List[str] = Field(default_factory=list)
    detected_documents: List[str] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)
    validation_notes: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class PolicyAgentOutput(BaseModel):
    policy_found: bool = False
    policy_valid: bool = False
    coverage_applicable: bool = False
    coverage_type: str = "Unavailable"
    policy_start_date: str = "Unavailable"
    policy_end_date: str = "Unavailable"
    coverage_limit: float = 0.0
    deductible: float = 0.0
    relevant_clauses: List[str] = Field(default_factory=list)
    policy_findings: List[str] = Field(default_factory=list)
    missing_documents: List[str] = Field(default_factory=list)
    explanation: str = ""


class FraudIndicator(BaseModel):
    type: str
    severity: Literal["Low", "Medium", "High"]
    source: Literal["Rule-Based Check", "AI Pattern Analysis"]
    evidence: str


class FraudAgentOutput(BaseModel):
    risk_score: int = Field(default=0, ge=0, le=100)
    risk_level: Literal["Low", "Medium", "High"] = "Low"
    indicators: List[FraudIndicator] = Field(default_factory=list)
    rule_checks_triggered: List[str] = Field(default_factory=list)
    ai_observations: List[str] = Field(default_factory=list)
    explanation: str = ""
    requires_manual_review: bool = True


class ClaimAssessmentOutput(BaseModel):
    claim_summary: str
    policy_verification_status: str
    fraud_risk_level: Literal["Low", "Medium", "High"]
    fraud_risk_score: int
    fraud_indicators: List[FraudIndicator] = Field(default_factory=list)
    missing_documents: List[str] = Field(default_factory=list)
    unresolved_questions: List[str] = Field(default_factory=list)
    estimated_eligible_amount: Optional[float] = None
    explanation: str
    recommended_next_action: Literal[
        "Ready for Human Review",
        "Additional Documents Required",
        "Policy Verification Required",
        "Investigation Recommended",
    ]
    human_review_required: bool = True


# ==========================================
# Claim & Workflow Schemas
# ==========================================
class ClaimCreateForm(BaseModel):
    policyholder_name: str = Field(..., min_length=2, max_length=120)
    policyholder_email: Optional[str] = ""
    policyholder_phone: Optional[str] = ""
    policy_number: str = Field(..., min_length=3, max_length=50)
    vehicle_number: str = Field(..., min_length=4, max_length=30)
    vehicle_model: str = Field(..., min_length=2, max_length=80)
    accident_date: str = Field(..., min_length=8, max_length=30)
    accident_time: Optional[str] = ""
    accident_location: str = Field(..., min_length=2, max_length=150)
    claimed_amount: float = Field(..., gt=0)
    estimated_damage_amount: Optional[float] = None
    damage_description: str = Field(..., min_length=5, max_length=2000)


class ProcessTriggerRequest(BaseModel):
    use_demo_mode: Optional[bool] = None


class HumanReviewRequest(BaseModel):
    action: Literal[
        "Mark Reviewed",
        "Request Additional Documents",
        "Mark Under Investigation",
        "Approve Payout Recommendation",
        "Reject Claim",
    ]
    notes: str = Field(..., min_length=3, max_length=2000)
    approved_amount: Optional[float] = None
    requested_documents: List[str] = Field(default_factory=list)


class AgentStageStatus(BaseModel):
    agent_id: str
    agent_name: str
    status: Literal["pending", "running", "completed", "failed"]
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None
    key_findings: List[str] = Field(default_factory=list)
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
