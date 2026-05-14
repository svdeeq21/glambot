import logging
from fastapi import APIRouter, Request, HTTPException
from app.services.pipeline import process_message
from app.services.whatsapp import send_text
from app.core.config import settings, business
from app.core.leads import (
    is_active, is_known, verify, pause, check_referral_tag,
    is_done_keyword, init_verified,
)

logger = logging.getLogger("glam-bot")
router = APIRouter()

# Pre-load whitelist on import
init_verified()


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

    # ─── Filter 1: Ignore messages sent by the bot itself ──────────
    if key.get("fromMe", False):
        return {"status": "ignored_fromme"}

    remote_jid = key.get("remoteJid", "")
    if not remote_jid:
        return {"status": "ignored_no_jid"}

    # ─── Filter 2: Ignore groups and broadcasts ────────────────────
    if "@g.us" in remote_jid:
        logger.info(f"[FILTER] Ignored group message from {remote_jid}")
        return {"status": "ignored_group"}

    if "@broadcast" in remote_jid or "status@" in remote_jid:
        return {"status": "ignored_broadcast"}

    # Only accept normal WhatsApp DMs (@s.whatsapp.net)
    if "@s.whatsapp.net" not in remote_jid:
        logger.info(f"[FILTER] Ignored non-DM JID: {remote_jid}")
        return {"status": "ignored_non_dm"}

    phone = remote_jid.replace("@s.whatsapp.net", "")

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

    # ─── Filter 3: Lead-state gating ───────────────────────────────
    # Tag check happens first: a valid tag either wakes a paused lead
    # or admits a fresh one.
    tag = check_referral_tag(text)

    if tag:
        verify(phone)
        if is_known(phone):
            logger.info(f"[RESUMED] Lead {phone} re-engaged via tag {tag}")
        else:
            logger.info(f"[VERIFIED] New lead {phone} entered via tag {tag}")
    elif not is_active(phone):
        # No tag AND not currently active → silently drop.
        # Covers: unverified strangers + paused leads (Fatima is handling them)
        logger.info(f"[FILTER] Ignored inactive {phone}: {text[:60]}")
        return {"status": "ignored_inactive"}

    # ─── Filter 4: DONE keyword → pause bot, hand off to Fatima ────
    if is_done_keyword(text):
        from app.services.whatsapp import notify_owner
        await send_text(
            phone,
            "Perfect! Your order is on its way 🎉\n\n"
            f"{business.get('owner_name', 'Fatima')} will reach out personally "
            "to confirm payment and finalize everything.\n\n"
            "Thank you for choosing us! ✨"
        )
        await notify_owner(
            f"🟢 *Lead ready for handoff*\n\n"
            f"📞 Phone: {phone}\n"
            f"💬 They said: \"{text}\"\n\n"
            f"Bot is now paused. Take it from here."
        )
        pause(phone)
        logger.info(f"[PAUSED] {phone} confirmed done. Bot handed off.")
        return {"status": "paused"}

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
