"""
Tracks which phone numbers have been "verified" through a referral tag.
Once verified, all subsequent messages from them get processed normally.

For production: swap this in-memory set with Redis or Supabase.
"""

from app.core.config import business

_verified: set[str] = set()


def init_verified():
    """Pre-load whitelist numbers as verified leads on startup."""
    whitelist = business.get("whitelist", []) or []
    for number in whitelist:
        _verified.add(str(number))


def is_verified(phone: str) -> bool:
    """Check if a phone number is already a verified lead."""
    return phone in _verified


def verify(phone: str):
    """Mark a phone number as a verified lead."""
    _verified.add(phone)


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
