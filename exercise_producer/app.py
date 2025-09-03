import os, logging, hashlib
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

load_dotenv()

SECRET_VALUE = os.getenv("SECRET_VALUE")  # injected via Secret Manager
DEFAULT_NAME = os.getenv("DEFAULT_NAME", "Student")

app = FastAPI(title="Exercise Producer", version="1.0.0")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("producer")


@app.get("/")
def root():
    return {"service": "exercise-producer", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "ok", "has_secret": bool(SECRET_VALUE), "default_name": DEFAULT_NAME}


@app.get("/produce")
def produce(name: Optional[str] = None):
    if SECRET_VALUE is None:
        raise HTTPException(status_code=500, detail="SECRET_VALUE not configured")

    person = name or DEFAULT_NAME
    now = datetime.now(timezone.utc).isoformat()

    # Use the secret without leaking it: include a short signature derived from it
    signature = hashlib.sha256((person + SECRET_VALUE).encode("utf-8")).hexdigest()[:12]

    payload = {
        "produced_at": now,
        "name": person,
        "message": f"Hello, {person}!",
        "signature": signature,
        "version": "1.0.0",
    }
    logger.info("Produced payload for %s", person)
    return payload
