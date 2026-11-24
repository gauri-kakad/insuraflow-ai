from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.database import Database
from config import settings
from utils.logger import logger

_client: MongoClient | None = None
_db: Database | None = None


def get_database() -> Database:
    global _client, _db
    if _db is None:
        logger.info(f"Connecting to MongoDB at {settings.MONGODB_URI} (db={settings.MONGODB_DB_NAME})")
        _client = MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)
        _db = _client[settings.MONGODB_DB_NAME]
        ensure_indexes(_db)
    return _db


def ensure_indexes(db: Database) -> None:
    try:
        db.users.create_index([("email", ASCENDING)], unique=True)
        db.policies.create_index([("policy_number", ASCENDING)], unique=True)
        db.policies.create_index([("vehicle_number", ASCENDING)])

        db.claims.create_index([("claim_id", ASCENDING)], unique=True)
        db.claims.create_index([("policy_number", ASCENDING)])
        db.claims.create_index([("vehicle_number", ASCENDING)])
        db.claims.create_index([("submitted_at", DESCENDING)])
        db.claims.create_index([("status", ASCENDING)])
        db.claims.create_index([("risk_level", ASCENDING)])

        db.agent_executions.create_index([("claim_id", ASCENDING), ("started_at", DESCENDING)])
        db.assessments.create_index([("claim_id", ASCENDING)], unique=True)
        db.audit_logs.create_index([("claim_id", ASCENDING), ("timestamp", DESCENDING)])
    except Exception as exc:
        logger.warning(f"MongoDB index creation deferred or failed: {exc}")


def close_database() -> None:
    global _client, _db
    if _client is not None:
        _client.close()
        _client = None
        _db = None
