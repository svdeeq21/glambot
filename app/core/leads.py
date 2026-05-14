"""
Tracks the state of each phone number that interacts with the bot.

States:
  - "active" → bot engages normally
  - "paused" → bot stays silent (Fatima has taken over)

Lifecycle:
  unverified --[valid tag]-->  active
  active     --[DONE]-->       paused
  paused     --[valid tag]-->  active   (re-entry via ad link)

For production: swap this in-memory dict with Redis or Supabase.
"""

from app.core.config import business

# {phone: "active" | "paused"}
_leads: dict[str, str] = {}


def init_verified():
    """Pre-load whitelist numbers as active leads on startup."""
    whitelist = business.get("whitelist", []) or []
    for number in whitelist:
        _leads[str(number)] = "active"


def is_active(phone: str) -> bool:
    """Bot should respond to this phone right now."""
    return _leads.get(phone) == "active"


def is_known(phone: str) -> bool:
    """Phone has been seen before (active OR paused)."""
    return phone in _leads


def verify(phone: str):
    """Mark a phone as active. Bot engages."""
    _leads[phone] = "active"


def pause(phone: str):
    """Pause bot for this phone. Fatima takes over manually."""
    _leads[phone] = "paused"


def check_referral_tag(text: str) -> str | None:
    """
    Check if a message contains a valid referral tag.
    Returns the matched tag if found, else None.
    """
    tags = business.get("referral_tags", []) or []
    text_upper = text.upper()
    for tag in tags:
        if tag.upper() in text_upper:
            return tag
    return None


def is_done_keyword(text: str) -> bool:
    """
    Customer wants to finish. Triggers bot handoff to Fatima.
    Triggered by 'DONE', 'CONFIRM', 'COMPLETE', 'CHECKOUT' (case-insensitive).
    """
    keywords = {"done", "confirm", "complete", "checkout"}
    text_clean = text.strip().lower()
    if text_clean in keywords:
        return True
    words = text_clean.split()
    if len(words) <= 2 and any(w in keywords for w in words):
        return True
    return False
