# Glam Bot — WhatsApp Booking Bot for Beauty Businesses

A fully working WhatsApp bot for makeup artists, nail technicians, hair stylists, and beauty businesses. Handles customer inquiries, shows price lists, answers FAQs, and books appointments — all via WhatsApp.

---

## Features

- Greets customers and shows a service menu
- Displays price list from a simple config file
- Shows working hours
- Answers common FAQs (home service, payment, rescheduling)
- Collects service preference, date, and customer name
- Confirms booking to the customer
- Alerts the business owner via WhatsApp immediately

---

## Stack

- **FastAPI** — backend (hosted on Render)
- **Evolution API** — WhatsApp gateway (hosted on Railway)
- **In-memory sessions** — no database needed for the demo

---

## Deployment Steps

### 1. Push to GitHub

Create a new repo and push this codebase.

### 2. Deploy to Render

1. Go to [render.com](https://render.com) → New → Web Service
2. Connect your GitHub repo
3. Set the following env vars:

| Key | Value |
|---|---|
| `EVOLUTION_API_URL` | `https://evolution-api-production-17af.up.railway.app` |
| `EVOLUTION_API_KEY` | Your Evolution API key |
| `EVOLUTION_INSTANCE` | `glam-bot` |
| `ADMIN_WHATSAPP` | Owner's number (e.g. `2348100000000`) |

4. Build command: `pip install -r requirements.txt`
5. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Deploy. Note your Render URL (e.g. `https://glam-bot.onrender.com`)

### 3. Create WhatsApp Instance

Call this endpoint once after deploy:

```
GET https://glam-bot.onrender.com/setup/create-instance
```

### 4. Connect WhatsApp (Scan QR)

```
GET https://glam-bot.onrender.com/setup/qr
```

Scan the returned QR code with the business WhatsApp number.

### 5. Register Webhook

```
POST https://glam-bot.onrender.com/setup/webhook?render_url=https://glam-bot.onrender.com
```

This tells Evolution API where to send incoming messages.

### 6. Test It

Send "Hi" to the connected WhatsApp number. The bot will respond.

---

## Customising for a Client

All business settings live in one file: `config/business.yml`

Edit it to change:
- Business name, owner name, WhatsApp number
- Services and prices
- Working hours
- Available booking dates
- FAQs

No code changes needed.

---

## File Structure

```
glam-bot/
├── app/
│   ├── api/
│   │   └── routes.py          # Webhook + setup endpoints
│   ├── core/
│   │   ├── config.py          # Settings + config loader
│   │   └── session.py         # In-memory conversation state
│   ├── services/
│   │   ├── pipeline.py        # Conversation state machine
│   │   └── whatsapp.py        # Evolution API client
│   └── main.py                # FastAPI app
├── config/
│   └── business.yml           # ← Owner edits this file
├── requirements.txt
├── render.yaml
└── .env.example
```
