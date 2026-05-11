import logging
from fastapi import APIRouter, Request, HTTPException
from app.services.pipeline import process_message
from app.services.whatsapp import send_text
from app.core.config import settings, business

logger = logging.getLogger("glam-bot")
router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok", "bot": business["name"]}


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event = body.get("event", "")
    data = body.get("data", {})

    if event != "messages.upsert":
        return {"status": "ignored"}

    message = data.get("message", {})
    key = data.get("key", {})

    # Ignore messages sent by the bot itself
    if key.get("fromMe", False):
        return {"status": "ignored"}

    phone = key.get("remoteJid", "").replace("@s.whatsapp.net", "")
    if not phone:
        return {"status": "ignored"}

    # Extract text from different message types
    text = (
        message.get("conversation")
        or message.get("extendedTextMessage", {}).get("text")
        or message.get("buttonsResponseMessage", {}).get("selectedButtonId")
        or message.get("listResponseMessage", {}).get("singleSelectReply", {}).get("selectedRowId")
        or ""
    ).strip()

    if not text:
        return {"status": "no_text"}

    logger.info(f"[WEBHOOK] {phone}: {text[:80]}")
    await process_message(phone, text)
    return {"status": "ok"}


@router.get("/setup/create-instance")
async def create_instance():
    """One-time call to create the Evolution API WhatsApp instance."""
    import httpx
    url = f"{settings.EVOLUTION_API_URL}/instance/create"
    headers = {"apikey": settings.EVOLUTION_API_KEY, "Content-Type": "application/json"}
    payload = {
        "instanceName": settings.EVOLUTION_INSTANCE,
        "qrcode": True,
        "integration": "WHATSAPP-BAILEYS"
    }
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(url, json=payload, headers=headers)
        return r.json()


@router.get("/setup/qr")
async def get_qr():
    """Fetch QR code to connect WhatsApp."""
    import httpx
    url = f"{settings.EVOLUTION_API_URL}/instance/connect/{settings.EVOLUTION_INSTANCE}"
    headers = {"apikey": settings.EVOLUTION_API_KEY}
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(url, headers=headers)
        return r.json()


@router.post("/setup/webhook")
async def configure_webhook(render_url: str):
    """Register this backend as the webhook in Evolution API."""
    import httpx
    url = f"{settings.EVOLUTION_API_URL}/webhook/set/{settings.EVOLUTION_INSTANCE}"
    headers = {"apikey": settings.EVOLUTION_API_KEY, "Content-Type": "application/json"}
    payload = {
        "url": f"{render_url}/webhook/whatsapp",
        "webhook_by_events": False,
        "webhook_base64": False,
        "events": ["MESSAGES_UPSERT"]
    }
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(url, json=payload, headers=headers)
        return r.json()


@router.get("/config/prices")
async def get_prices():
    """Return the current price list."""
    return {
        "business": business["name"],
        "services": business["services"],
        "availability": business["availability"]
    }
