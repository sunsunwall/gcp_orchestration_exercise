import os, json
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from google.cloud import bigquery

load_dotenv()

USE_IAM_AUTH = os.getenv("USE_IAM_AUTH", "true").lower() in ("1", "true", "yes")

# BigQuery configuration
BQ_PROJECT = os.getenv("BQ_PROJECT")  # optional; falls back to ADC project if not provided
BQ_DATASET = os.getenv("BQ_DATASET", "raw_data")
BQ_TABLE = os.getenv("BQ_TABLE", "weather_raw")

app = FastAPI(title="Weather Writer API", version="1.0.0")


def call_fetcher(location: Optional[str], date: Optional[str]) -> Dict[str, Any]:
    raise HTTPException(status_code=501, detail="Pull mode disabled; use POST /write from fetcher")


_table_ready = False


def ensure_table(client: bigquery.Client) -> str:
    global _table_ready
    table_id = f"{BQ_PROJECT or client.project}.{BQ_DATASET}.{BQ_TABLE}"
    if _table_ready:
        return table_id

    # Ensure dataset
    dataset_ref = bigquery.DatasetReference(BQ_PROJECT or client.project, BQ_DATASET)
    try:
        client.get_dataset(dataset_ref)
    except Exception:
        client.create_dataset(bigquery.Dataset(dataset_ref), exists_ok=True)

    # Ensure table with desired schema
    schema = [
        bigquery.SchemaField("raw_json", "STRING"),
        bigquery.SchemaField("source_url", "STRING"),
        bigquery.SchemaField("fetched_at", "TIMESTAMP"),
    ]
    table = bigquery.Table(table_id, schema=schema)
    try:
        client.get_table(table)
    except Exception:
        client.create_table(table, exists_ok=True)

    _table_ready = True
    return table_id


def write_to_bigquery_raw(payload: Dict[str, Any], source_url: str, fetched_at: str) -> Dict[str, Any]:
    client = bigquery.Client(project=BQ_PROJECT) if BQ_PROJECT else bigquery.Client()
    table_id = ensure_table(client)

    row = {
        "raw_json": json.dumps(payload, ensure_ascii=False),
        "source_url": source_url,
        "fetched_at": fetched_at,
    }
    # Idempotency: use a stable id based on source_url + fetched_at
    row_id = f"{source_url}:{fetched_at}"
    errors = client.insert_rows_json(table_id, [row], row_ids=[row_id])
    if errors:
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
    # Raw JSON passthrough; take source_url from header if provided by fetcher
    source_url = os.getenv("DEFAULT_SOURCE_URL", "")
    try:
        import fastapi
        request = fastapi.Request  # type: ignore[attr-defined]
    except Exception:
        request = None  # fallback if injection fails in some runtimes

    # FastAPI will inject Request if declared; but we keep function simple
    # Instead, allow clients to embed source_url in body under _meta.source_url
    embedded_source = (
        body.get("_meta", {}).get("source_url") if isinstance(body.get("_meta"), dict) else None
    )
    source_url = embedded_source or source_url

    from datetime import datetime, timezone
    fetched_at = datetime.now(timezone.utc).isoformat()

    result = write_to_bigquery_raw(body, str(source_url or ""), fetched_at)
    return {"status": "ok", **result}


