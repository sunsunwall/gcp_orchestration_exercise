# Cloud Functions Version of Weather Ingestion

## Key Differences from FastAPI Service and Cloud Run Job

### **Cloud Function** (`main.py`):
- **Entry point**: `@functions_framework.http` decorator
- **No FastAPI**: Uses Google's functions framework
- **Request handling**: Direct Flask-like request object
- **Error handling**: Return error response (don't raise exceptions)
- **Deployment**: Just upload code (no Docker)

## Comparison

| Aspect | FastAPI Service | Cloud Run Job | Cloud Function |
|--------|-----------------|---------------|----------------|
| **Framework** | FastAPI + Uvicorn | Pure Python script | functions-framework |
| **HTTP Interface** | ✅ Full REST API | ❌ No HTTP | ✅ Single HTTP endpoint |
| **Containerization** | ✅ Docker required | ✅ Docker required | ❌ Just code |
| **Deployment** | Cloud Build + Docker | Cloud Build + Docker | **Direct upload** |
| **Runtime Limits** | Unlimited | Unlimited | **9 minutes max** |
| **Memory Limits** | Up to 32GB | Up to 32GB | **Up to 8GB** |
| **Cold Start** | ~1-3 seconds | ~1-3 seconds | **~100ms** |
| **Complexity** | Medium | Low | **Lowest** |

## CI/CD Deployment (Similar to FastAPI!)

**Cloud Functions CAN use GitHub + Cloud Build triggers!**

Students use the same workflow:
1. **Push code to GitHub**
2. **Cloud Build trigger fires automatically** 
3. **`cloudbuild.yaml` runs `gcloud functions deploy`**

It's like FastAPI, but no Docker - just code upload!

### Example cloudbuild.yaml
```yaml
steps:
  - name: 'gcr.io/cloud-builders/gcloud'
    args:
      - functions
      - deploy
      - weather-ingestion
      - '--runtime=python311'
      - '--trigger-http'
      - '--entry-point=weather_ingestion'
      - '--source=.'
      - '--env-vars-file=env.yaml'
      - '--set-secrets=API_KEY=WEATHER_API_KEY:latest'
      - '--region=europe-north2'
```

**Architecture:**
```
Scheduler → HTTP POST → Cloud Function → BigQuery
```

This fits your teaching model perfectly!

## Advantages of Cloud Functions

1. **Simplest deployment**: No Docker, no build steps (but requires CLI)
2. **Fastest cold starts**: ~100ms vs ~1-3s for containers
3. **Lowest operational overhead**: Google manages everything
4. **Built-in scaling**: 0 to 1000+ instances automatically
5. **Cost effective**: Pay only for execution time

## Disadvantages of Cloud Functions

1. **Runtime limits**: 9 minutes max execution time
2. **Less flexibility**: Can't customize runtime environment
3. **Vendor lock-in**: More GCP-specific than containers
4. **Limited debugging**: Fewer debugging tools vs containers

## For Your Daily Weather Pipeline

**Cloud Functions is perfect because:**
- Simple daily job (well under 9 minute limit)
- No complex dependencies
- Want minimal operational overhead
- Cost optimization (only pay for ~30 seconds/day)

**Use FastAPI Services if:**
- You want to teach microservices patterns
- Need full REST API capabilities
- Want container portability
- Building larger system with multiple endpoints

**Use Cloud Run Jobs if:**
- Need longer execution times
- Want container benefits without HTTP
- Building batch processing pipelines
- Need custom runtime environments
