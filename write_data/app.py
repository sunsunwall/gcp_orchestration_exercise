import os, json, logging
from typing import Any, Dict

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from google.cloud import bigquery

load_dotenv()

# BigQuery configuration
BQ_PROJECT = os.getenv("BQ_PROJECT")  # optional; falls back to ADC project if not provided
BQ_DATASET = os.getenv("BQ_DATASET", "raw_data")
BQ_TABLE = os.getenv("BQ_TABLE", "weather_raw")

app = FastAPI(title="Weather Writer API", version="1.0.0")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("writer")

def write_to_bigquery_raw(payload: Dict[str, Any], source_url: str, fetched_at: str) -> Dict[str, Any]:
    client = bigquery.Client(project=BQ_PROJECT) if BQ_PROJECT else bigquery.Client()
    project_id = BQ_PROJECT or client.project
    table_id = f"{project_id}.{BQ_DATASET}.{BQ_TABLE}"

    row = {
        "raw_json": json.dumps(payload, ensure_ascii=False),
        "source_url": source_url,
        "fetched_at": fetched_at,
    }
    # Idempotency: use a stable id based on source_url + fetched_at
    row_id = f"{source_url}:{fetched_at}"
    logger.info(f"Writing row to {table_id}")
    errors = client.insert_rows_json(table_id, [row], row_ids=[row_id])
    if errors:
        # In a real system, add retry/backoff and structured error handling
        raise HTTPException(status_code=500, detail=f"BQ insert errors: {errors}")
    return {"table": table_id, "inserted": 1}


@app.get("/")
def root():
    return {"service": "Weather Writer API", "version": "1.0.0", "docs": "/docs"}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "bq_dataset": BQ_DATASET,
        "bq_table": BQ_TABLE,
        "bq_project": BQ_PROJECT,
    }


@app.post("/write")
async def write_event(body: Dict[str, Any]):
    source_url = str(body.get("source_url", ""))
    from datetime import datetime, timezone
    fetched_at = datetime.now(timezone.utc).isoformat()

    logger.info("Received payload; writing to BigQuery")
    result = write_to_bigquery_raw(body, source_url, fetched_at)
    return {"status": "ok", **result}


