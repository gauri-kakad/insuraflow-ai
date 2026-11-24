from fastapi import APIRouter, HTTPException, status, Depends
from database import get_database
from models.schemas import LoginRequest, TokenResponse, UserResponse
from utils.security import verify_password, create_access_token, get_current_user
from config import settings

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    db = get_database()
    user = db.users.find_one({"email": payload.email.lower().strip()})
    if not user or not verify_password(payload.password, user.get("hashed_password", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    token = create_access_token({"sub": user["email"], "role": user["role"]})
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            user_id=user["user_id"],
            name=user["name"],
            email=user["email"],
            role=user["role"],
            department=user["department"],
        ),
    )


@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "user": current_user,
        "system_capabilities": {
            "live_gemini_configured": settings.has_live_gemini,
            "gemini_model": settings.GEMINI_MODEL,
            "demo_mode_enabled": settings.ENABLE_DEMO_MODE,
        },
    }
