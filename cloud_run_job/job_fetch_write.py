import os, json, logging, sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import requests
from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()

API_KEY = os.getenv("API_KEY")
LOCATION = os.getenv("LOCATION", "59.3293,18.0686")
DATE = os.getenv("DATE")  # optional override; otherwise yesterday

BQ_PROJECT = os.getenv("BQ_PROJECT")
BQ_DATASET = os.getenv("BQ_DATASET", "raw_data")
BQ_TABLE = os.getenv("BQ_TABLE", "weather_raw")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("job_fetch_write")


def get_default_date() -> str:
    return (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")


def build_source_url(location: str, date: str) -> str:
    base = "https://api.weatherapi.com/v1/history.json"
    # do not include API key in stored source URL
    return f"{base}?q={location}&dt={date}"


def fetch_weather(location: str, date: str) -> Dict[str, Any]:
    api_key = os.getenv("API_KEY")
    if not api_key:
        logger.error("API_KEY not configured")
        sys.exit(1)
    
    url = "https://api.weatherapi.com/v1/history.json"
    params = {"key": api_key, "q": location, "dt": date}
    
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch weather data: {e}")
        sys.exit(1)


def write_raw(payload: Dict[str, Any], source_url: str, fetched_at: str) -> Dict[str, Any]:
    try:
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
            logger.error(f"BQ insert errors: {errors}")
            sys.exit(1)
            
        return {"table": table_id, "inserted": 1}
    
    except Exception as e:
        logger.error(f"Failed to write to BigQuery: {e}")
        sys.exit(1)


def main():
    """Main job execution function"""
    logger.info("Starting weather ingestion job")
    
    # Get parameters (from env vars or defaults)
    loc = LOCATION
    d = DATE or get_default_date()
    
    logger.info(f"Fetching weather for {loc} on {d}")
    
    # Fetch weather data
    payload = fetch_weather(loc, d)
    
    # Prepare metadata
    source_url = build_source_url(loc, d)
    fetched_at = datetime.now(timezone.utc).isoformat()
    
    # Write to BigQuery
    logger.info("Writing to BigQuery")
    result = write_raw(payload, source_url, fetched_at)
    
    logger.info(f"Job completed successfully: {result}")
    print(json.dumps({
        "status": "success",
        "location": loc,
        "date": d,
        **result
    }))


if __name__ == "__main__":
    main()