import os, json
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from datetime import datetime, timedelta, timezone
from google.oauth2 import id_token
from google.auth.transport.requests import Request as GoogleAuthRequest

load_dotenv()

# Read API key lazily at request time to avoid crashing if missing at startup
# and to allow different environments to inject it dynamically.
API_KEY   = os.getenv("API_KEY")
LOCATION  = os.environ.get("LOCATION", "59.3293,18.0686")
DATE      = os.environ.get("DATE")
WRITER_URL = os.environ.get("WRITER_URL")  # e.g., https://writer-xyz.a.run.app/write
WRITER_AUDIENCE = os.environ.get("WRITER_AUDIENCE", WRITER_URL)
USE_IAM_AUTH = os.environ.get("USE_IAM_AUTH", "true").lower() in ("1", "true", "yes")

app = FastAPI(title="Weather Ingestion API", version="1.0.0")


def get_default_date() -> str:
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    return yesterday.strftime("%Y-%m-%d")


def fetch_weather(location: str, date: str) -> dict:
    api_key = os.getenv("API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="API_KEY not configured")
    url = "http://api.weatherapi.com/v1/history.json"
    params = {"key": api_key, "q": location, "dt": date}
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def write_weather(data: dict, filename: str = "weather.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


@app.get("/")
def welcome_page():
   
    return {
        "service": "Weather Ingestion API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
def health():
    return {"status": "ok", "has_api_key": bool(os.getenv("API_KEY")), "default_location": LOCATION, "default_date": (DATE or get_default_date())}


@app.get("/weather")
def get_weather(location: str | None = None, date: str | None = None):
    loc = location or LOCATION
    d = date or DATE or get_default_date()
    return fetch_weather(loc, d)


@app.post("/ingest")
def ingest(location: str | None = None, date: str | None = None):
    if not WRITER_URL:
        raise HTTPException(status_code=500, detail="WRITER_URL not configured")

    loc = location or LOCATION
    d = date or DATE or get_default_date()
    data = fetch_weather(loc, d)

    headers = {"Content-Type": "application/json"}
    if USE_IAM_AUTH and WRITER_AUDIENCE:
        token = id_token.fetch_id_token(GoogleAuthRequest(), WRITER_AUDIENCE)
        if not token:
            raise HTTPException(status_code=500, detail="Failed to obtain ID token for writer")
        headers["Authorization"] = f"Bearer {token}"

    response = requests.post(WRITER_URL, headers=headers, json=data, timeout=60)
    response.raise_for_status()
    return {"status": "sent", "writer_status": response.status_code, "location": loc, "date": d}
