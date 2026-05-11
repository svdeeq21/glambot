from datetime import datetime, timedelta
from typing import Optional

# Simple in-memory store: {phone: session_dict}
# For production swap this with Redis
_sessions: dict[str, dict] = {}
SESSION_TTL_MINUTES = 60


def get_session(phone: str) -> dict:
    session = _sessions.get(phone)
    if session:
        if datetime.utcnow() - session["last_active"] > timedelta(minutes=SESSION_TTL_MINUTES):
            del _sessions[phone]
            return _new_session()
        return session
    return _new_session()


def save_session(phone: str, session: dict):
    session["last_active"] = datetime.utcnow()
    _sessions[phone] = session


def clear_session(phone: str):
    _sessions.pop(phone, None)


def _new_session() -> dict:
    return {
        "state": "GREETING",
        "selected_service": None,
        "selected_date": None,
        "name": None,
        "last_active": datetime.utcnow(),
    }
