import logging
from datetime import datetime
from app.core.config import business, settings
from app.core.session import get_session, save_session, clear_session
from app.services.whatsapp import send_text, send_buttons, notify_owner

logger = logging.getLogger("glam-bot")

# ── Helpers ──────────────────────────────────────────────────────────────────

def _price_list() -> str:
    lines = ["Here's our current price list:\n"]
    for s in business["services"]:
        price = f"₦{s['price']:,}"
        lines.append(f"{s['emoji']} {s['name']} — {price}")
    return "\n".join(lines)


def _hours() -> str:
    h = business["hours"]
    lines = ["Our working hours:\n"]
    days = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]
    labels = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    for day, label in zip(days, labels):
        lines.append(f"📅 {label}: {h.get(day, 'Closed')}")
    return "\n".join(lines)


def _available_dates() -> list[str]:
    today = datetime.utcnow().date()
    dates = []
    for d in business["availability"]:
        dt = datetime.strptime(d, "%Y-%m-%d").date()
        if dt >= today:
            dates.append(dt)
    dates.sort()
    return [d.strftime("%A, %d %B %Y") for d in dates[:6]]  # Show next 6 slots


def _services_menu() -> list[str]:
    return [s["name"] for s in business["services"]]


def _match_service(text: str) -> dict | None:
    text_lower = text.lower()
    for s in business["services"]:
        if s["name"].lower() in text_lower or text_lower in s["name"].lower():
            return s
    # Try matching by number
    try:
        idx = int(text.strip()) - 1
        if 0 <= idx < len(business["services"]):
            return business["services"][idx]
    except ValueError:
        pass
    return None


def _match_faq(text: str) -> str | None:
    text_lower = text.lower()
    keywords = {
        "location": ["come to", "home service", "location", "travel", "house"],
        "bring": ["bring", "need to carry", "prepare"],
        "pay": ["pay", "payment", "transfer", "cash", "deposit"],
        "reschedule": ["reschedule", "cancel", "change date", "postpone"],
    }
    for faq in business["faqs"]:
        for kw_list in keywords.values():
            if any(kw in text_lower for kw in kw_list):
                for faq2 in business["faqs"]:
                    if any(kw in faq2["question"].lower() for kw in kw_list):
                        return faq2["answer"]
    return None


def _match_date(text: str, available: list[str]) -> str | None:
    text_lower = text.lower().strip()
    for date in available:
        if text_lower in date.lower():
            return date
    try:
        idx = int(text.strip()) - 1
        if 0 <= idx < len(available):
            return available[idx]
    except ValueError:
        pass
    return None


# ── State Handlers ────────────────────────────────────────────────────────────

async def handle_greeting(phone: str, session: dict):
    name = business["name"]
    owner = business["owner"]["name"] if "owner" in business else business.get("owner_name", "us")
    msg = (
        f"Hi! 👋 Welcome to *{name}*.\n\n"
        f"I'm {owner}'s virtual assistant. I can help you with:\n\n"
        f"💄 Price list\n📅 Book an appointment\n🕐 Working hours\n❓ FAQs\n\n"
        f"What would you like?"
    )
    await send_buttons(phone, msg, ["See prices", "Book appointment", "Working hours", "Ask a question"])
    session["state"] = "MAIN_MENU"


async def handle_main_menu(phone: str, text: str, session: dict):
    t = text.lower()

    if any(w in t for w in ["price", "cost", "how much", "1"]):
        await send_text(phone, _price_list() + "\n\n_Would you like to book an appointment?_")
        await send_buttons(phone, "", ["Yes, book now", "Working hours", "Ask a question"])
        session["state"] = "POST_PRICES"

    elif any(w in t for w in ["book", "appointment", "date", "schedule", "2"]):
        session["state"] = "SELECT_SERVICE"
        await send_buttons(
            phone,
            "Which service would you like to book? 💅",
            _services_menu()
        )

    elif any(w in t for w in ["hour", "time", "open", "when", "3"]):
        await send_text(phone, _hours())
        await send_buttons(phone, "", ["Book appointment", "See prices", "Ask a question"])
        session["state"] = "MAIN_MENU"

    elif any(w in t for w in ["ask", "question", "faq", "4"]):
        await send_text(
            phone,
            "Sure! Ask me anything — home service, payment, what to bring, rescheduling... 😊"
        )
        session["state"] = "FAQ"

    else:
        # Try FAQ match first
        faq_answer = _match_faq(text)
        if faq_answer:
            await send_text(phone, faq_answer)
            await send_buttons(phone, "\nAnything else?", ["Book appointment", "See prices", "Working hours"])
            session["state"] = "MAIN_MENU"
        else:
            await send_buttons(
                phone,
                "Sorry, I didn't quite get that 😊 Here's what I can help with:",
                ["See prices", "Book appointment", "Working hours", "Ask a question"]
            )


async def handle_post_prices(phone: str, text: str, session: dict):
    t = text.lower()
    if any(w in t for w in ["yes", "book", "1"]):
        session["state"] = "SELECT_SERVICE"
        await send_buttons(phone, "Which service would you like to book? 💅", _services_menu())
    else:
        await handle_main_menu(phone, text, session)


async def handle_select_service(phone: str, text: str, session: dict):
    service = _match_service(text)
    if service:
        session["selected_service"] = service["name"]
        session["state"] = "SELECT_DATE"
        available = _available_dates()
        if not available:
            await send_text(
                phone,
                "Sorry, there are no available slots right now. Please check back soon or contact us directly! 🙏"
            )
            session["state"] = "MAIN_MENU"
            return
        slots = "\n".join([f"{i+1}. {d}" for i, d in enumerate(available)])
        await send_text(
            phone,
            f"Great choice! *{service['name']}* — ₦{service['price']:,} 💄\n\n"
            f"Here are our next available slots:\n\n{slots}\n\n"
            f"Reply with the number of your preferred date:"
        )
    else:
        await send_buttons(
            phone,
            "Please choose a service from the list:",
            _services_menu()
        )


async def handle_select_date(phone: str, text: str, session: dict):
    available = _available_dates()
    date = _match_date(text, available)
    if date:
        session["selected_date"] = date
        session["state"] = "COLLECT_NAME"
        await send_text(phone, f"Perfect! *{date}* it is 🎉\n\nLastly — what's your name so we can confirm your booking?")
    else:
        slots = "\n".join([f"{i+1}. {d}" for i, d in enumerate(available)])
        await send_text(
            phone,
            f"Please pick one of these available dates by replying with the number:\n\n{slots}"
        )


async def handle_collect_name(phone: str, text: str, session: dict):
    name = text.strip().title()
    session["name"] = name
    session["state"] = "CONFIRMED"

    service = session["selected_service"]
    date = session["selected_date"]
    biz = business["name"]

    # Confirm to customer
    await send_text(
        phone,
        f"You're all set, *{name}*! 🙌\n\n"
        f"📋 *Booking summary*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💄 Service: {service}\n"
        f"📅 Date: {date}\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"A *50% deposit* is required to secure your slot.\n\n"
        f"👉 Reply *DONE* to confirm your order. "
        f"{business.get('owner_name', 'Fatima')} will then reach out personally "
        f"with payment details and finalize everything.\n\n"
        f"See you soon! ✨"
    )

    # Alert the owner
    await notify_owner(
        f"🔔 *New Booking Request!*\n\n"
        f"👤 Name: {name}\n"
        f"📞 Phone: {phone}\n"
        f"💄 Service: {service}\n"
        f"📅 Date: {date}\n\n"
        f"Reply to confirm and send payment details."
    )

    logger.info(f"[BOOKING] {name} ({phone}) → {service} on {date}")


async def handle_faq(phone: str, text: str, session: dict):
    faq_answer = _match_faq(text)
    if faq_answer:
        await send_text(phone, faq_answer)
        await send_buttons(phone, "\nAnything else I can help with?", ["Book appointment", "See prices", "Working hours"])
        session["state"] = "MAIN_MENU"
    else:
        await send_text(
            phone,
            "I'm not sure about that one 😊 You can contact us directly for more info, "
            "or choose from the options below:"
        )
        await send_buttons(phone, "", ["Book appointment", "See prices", "Working hours"])
        session["state"] = "MAIN_MENU"


# ── Main Entry Point ──────────────────────────────────────────────────────────

async def process_message(phone: str, text: str):
    session = get_session(phone)
    state = session.get("state", "GREETING")

    logger.info(f"[MSG] {phone} | state={state} | text={text[:60]}")

    # Global resets
    if text.lower() in ["hi", "hello", "hey", "start", "menu", "help"]:
        session = {"state": "GREETING", "selected_service": None, "selected_date": None, "name": None}
        from app.core.session import _new_session
        await handle_greeting(phone, session)
        save_session(phone, session)
        return

    if state == "GREETING":
        await handle_greeting(phone, session)

    elif state == "MAIN_MENU":
        await handle_main_menu(phone, text, session)

    elif state == "POST_PRICES":
        await handle_post_prices(phone, text, session)

    elif state == "SELECT_SERVICE":
        await handle_select_service(phone, text, session)

    elif state == "SELECT_DATE":
        await handle_select_date(phone, text, session)

    elif state == "COLLECT_NAME":
        await handle_collect_name(phone, text, session)

    elif state == "CONFIRMED":
        await send_buttons(
            phone,
            "Your booking is being processed 🙏 Is there anything else you need?",
            ["Book another service", "See prices", "Working hours"]
        )
        session["state"] = "MAIN_MENU"

    elif state == "FAQ":
        await handle_faq(phone, text, session)

    else:
        session["state"] = "GREETING"
        await handle_greeting(phone, session)

    save_session(phone, session)
