import httpx
import logging
from app.core.config import settings

logger = logging.getLogger("glam-bot")


async def send_text(phone: str, message: str):
    """Send a plain text WhatsApp message."""
    url = f"{settings.EVOLUTION_API_URL}/message/sendText/{settings.EVOLUTION_INSTANCE}"
    headers = {"apikey": settings.EVOLUTION_API_KEY, "Content-Type": "application/json"}
    payload = {"number": phone, "text": message}

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            r = await client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            logger.info(f"[SENT] → {phone}: {message[:60]}...")
        except Exception as e:
            logger.error(f"[SEND_FAILED] {phone}: {e}")


async def send_buttons(phone: str, body: str, buttons: list[str]):
    """
    Send a message with quick-reply buttons.
    Falls back to numbered text list if Evolution API button sending fails.
    """
    # Build numbered fallback first (always works)
    numbered = body + "\n\n"
    for i, btn in enumerate(buttons, 1):
        numbered += f"{i}. {btn}\n"
    numbered += "\n_Reply with the number of your choice_"

    # Try buttons endpoint; fall back to plain text
    url = f"{settings.EVOLUTION_API_URL}/message/sendButtons/{settings.EVOLUTION_INSTANCE}"
    headers = {"apikey": settings.EVOLUTION_API_KEY, "Content-Type": "application/json"}
    payload = {
        "number": phone,
        "title": "",
        "description": body,
        "footer": "",
        "buttons": [{"buttonId": str(i), "buttonText": {"displayText": b}, "type": 1}
                    for i, b in enumerate(buttons, 1)]
    }

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            r = await client.post(url, json=payload, headers=headers)
            if r.status_code == 200:
                logger.info(f"[BUTTONS_SENT] → {phone}")
                return
        except Exception:
            pass

    # Fallback
    await send_text(phone, numbered)


async def notify_owner(message: str):
    """Send an alert to the business owner."""
    if settings.ADMIN_WHATSAPP:
        await send_text(settings.ADMIN_WHATSAPP, message)
