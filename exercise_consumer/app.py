import os, json, logging
from datetime import datetime, timezone
from typing import Any, Dict

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from google.cloud import storage

load_dotenv()

BUCKET = os.getenv("BUCKET")
FOLDER = os.getenv("FOLDER", "exercise/")

app = FastAPI(title="Exercise Consumer", version="1.0.0")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("consumer")


@app.get("/")
def root():
    return {"service": "exercise-consumer", "bucket": BUCKET, "folder": FOLDER}


@app.get("/health")
def health():
    return {"status": "ok", "has_bucket": bool(BUCKET)}


@app.post("/write")
async def write(request: Request):
    if not BUCKET:
        raise HTTPException(status_code=500, detail="BUCKET not configured")

    payload: Dict[str, Any] = await request.json()
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = payload.get("name", "unknown")
    dest = f"{FOLDER.rstrip('/')}/{now}_{name}.json"

    client = storage.Client()
    bucket = client.bucket(BUCKET)
    blob = bucket.blob(dest)
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    logger.info("Writing object gs://%s/%s", BUCKET, dest)
    blob.upload_from_string(data, content_type="application/json")
    return {"status": "ok", "gcs": f"gs://{BUCKET}/{dest}"}
