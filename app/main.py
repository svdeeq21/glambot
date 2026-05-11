import logging
from fastapi import FastAPI
from app.api.routes import router
from app.core.config import business

logging.basicConfig(level="INFO", format="%(asctime)s [%(levelname)s] %(message)s")

app = FastAPI(title=f"{business['name']} WhatsApp Bot", version="1.0.0")
app.include_router(router)
