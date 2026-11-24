from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import get_database, close_database
from services.seed_service import seed_database
from routes.auth_routes import router as auth_router
from routes.claim_routes import router as claim_router
from utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} API Server...")
    try:
        get_database()
        seed_database(force_reset=False)
    except Exception as exc:
        logger.error(f"Startup DB initialization warning: {exc}")
    yield
    close_database()
    logger.info(f"{settings.APP_NAME} API Server stopped.")


app = FastAPI(
    title="InsuraFlow AI — Multi-Agent Insurance Claims API",
    description=(
        "Enterprise decision-support API for motor insurance claim extraction, policy verification, "
        "hybrid fraud risk detection, and human-in-the-loop officer review."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(claim_router)


@app.get("/api/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "live_gemini_configured": settings.has_live_gemini,
        "demo_mode_enabled": settings.ENABLE_DEMO_MODE,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
