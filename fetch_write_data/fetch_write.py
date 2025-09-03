import os, json, logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from google.cloud import bigquery

load_dotenv()

API_KEY = os.getenv("API_KEY")
LOCATION = os.getenv("LOCATION", "59.3293,18.0686")
DATE = os.getenv("DATE")  # optional override; otherwise yesterday

BQ_PROJECT = os.getenv("BQ_PROJECT")
BQ_DATASET = os.getenv("BQ_DATASET", "raw_data")
BQ_TABLE = os.getenv("BQ_TABLE", "weather_raw")

app = FastAPI(title="Weather Fetch+Write", version="1.0.0")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fetch_write")


def get_default_date() -> str:
    return (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")


def build_source_url(location: str, date: str) -> str:
    base = "https://api.weatherapi.com/v1/history.json"
    # do not include API key in stored source URL
    return f"{base}?q={location}&dt={date}"


def fetch_weather(location: str, date: str) -> Dict[str, Any]:
    api_key = os.getenv("API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="API_KEY not configured")
    url = "https://api.weatherapi.com/v1/history.json"
    params = {"key": api_key, "q": location, "dt": date}
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def write_raw(payload: Dict[str, Any], source_url: str, fetched_at: str) -> Dict[str, Any]:
    client = bigquery.Client(project=BQ_PROJECT) if BQ_PROJECT else bigquery.Client()
    project_id = BQ_PROJECT or client.project
    table_id = f"{project_id}.{BQ_DATASET}.{BQ_TABLE}"
    row = {
        "raw_json": json.dumps(payload, ensure_ascii=False),
        "source_url": source_url,
        "fetched_at": fetched_at,
    }
    row_id = f"{source_url}:{fetched_at}"
    logger.info(f"Writing row to {table_id}")
    errors = client.insert_rows_json(table_id, [row], row_ids=[row_id])
    if errors:
        # For demo simplicity; in production add retries/handling
        raise HTTPException(status_code=500, detail=f"BQ insert errors: {errors}")
    return {"table": table_id, "inserted": 1}


@app.get("/")
def root():
    return {"service": "Weather Fetch+Write", "version": "1.0.0", "docs": "/docs"}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "has_api_key": bool(os.getenv("API_KEY")),
        "location_default": LOCATION,
        "date_default": (DATE or get_default_date()),
        "bq_dataset": BQ_DATASET,
        "bq_table": BQ_TABLE,
        "bq_project": BQ_PROJECT,
    }


@app.post("/run")
def run(location: str | None = None, date: str | None = None):
    loc = location or LOCATION
    d = date or DATE or get_default_date()
    logger.info(f"Fetching weather for {loc} {d}")
    payload = fetch_weather(loc, d)
    source_url = build_source_url(loc, d)
    fetched_at = datetime.now(timezone.utc).isoformat()
    logger.info("Writing to BigQuery")
    result = write_raw(payload, source_url, fetched_at)
    return {"status": "ok", "location": loc, "date": d, **result}
