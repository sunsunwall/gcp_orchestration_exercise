# FastAPI + Cloud Run Service Version of Weather Ingestion

This note covers your combined FastAPI app (`fetch_write_data/fetch_write.py`) for fetching weather data and writing to BigQuery, deployed as a Cloud Run service. It's the baseline you're teaching students - a microservice with HTTP endpoints and automated CI/CD.

## Key Differences from Cloud Run Job and Cloud Function

### **FastAPI Service** (`fetch_write.py`):
- **Entry point**: FastAPI `@app.post("/run")` decorator
- **Full HTTP interface**: Multiple endpoints (`/run`, `/health`, `/`)
- **Error handling**: Raise `HTTPException` for API errors
- **Deployment**: Containerized with Docker + Cloud Build
- **Execution**: Always ready for requests (scales to zero when idle)

## Comparison

| Aspect | FastAPI Service | Cloud Run Job | Cloud Function |
|--------|-----------------|---------------|----------------|
| **Framework** | **FastAPI + Uvicorn** | Pure Python script | functions-framework |
| **HTTP Interface** | **✅ Full REST API** | ❌ No HTTP | ✅ Single HTTP endpoint |
| **Containerization** | ✅ Docker required | ✅ Docker required | ❌ Just code |
| **Deployment** | Cloud Build + Docker | Cloud Build + Docker | Direct upload (or Cloud Build) |
| **Runtime Limits** | **Unlimited** | Unlimited | 9 minutes max |
| **Memory Limits** | **Up to 32GB** | Up to 32GB | Up to 8GB |
| **Cold Start** | ~1-3 seconds | ~1-3 seconds | ~100ms |
| **Execution Model** | **Always ready for requests** | Run once and exit | Triggered by requests |
| **Complexity** | **Medium** | Low | Lowest |

## CI/CD Deployment

standard GitHub + Cloud Build workflow:
1. **Code in GitHub** (e.g., update `fetch_write.py`)
2. **Push to trigger branch** (e.g., main)
3. **Cloud Build trigger fires automatically**
4. **`cloudbuild.yaml` builds Docker image + deploys to Cloud Run**



**Architecture:**
```
Scheduler → Workflows → HTTP POST → FastAPI Service → BigQuery
```
(Or simplify to Scheduler → HTTP POST for single service.)

## Advantages of FastAPI Services

1. **Teaching value**: Shows real microservices patterns (APIs, endpoints)
2. **Testability**: Students can curl endpoints to test manually
3. **Modularity**: Easy to separate fetch/write logic
4. **Flexibility**: Add more endpoints/routes easily
5. **Industry relevance**: Matches production web services
6. **CI/CD friendly**: Perfect for your GitHub + Cloud Build model
7. **Unlimited runtime**: No time limits for complex jobs

## Disadvantages of FastAPI Services

1. **HTTP overhead**: Need to handle requests/responses
2. **Slightly more complex code**: Framework boilerplate
3. **Security surface**: Exposed endpoints (mitigate with OIDC)
4. **Cold starts**: For infrequent calls (but scales to zero)

## For Your Daily Weather Pipeline

**FastAPI Services are perfect for teaching because:**
- Demonstrates end-to-end microservices (API + deployment)
- Fits your CI/CD workflow (GitHub push → auto deploy)
- Students can interact via HTTP (great for demos)
- Scales well for daily jobs while teaching valuable skills

**Use Cloud Run Jobs if:**
- Want pure batch (no HTTP)
- Need high resources without API overhead

**Use Cloud Functions if:**
- Want simplest non-container deployment
- OK with manual CLI (or custom Cloud Build)

## Code Structure Differences

### **FastAPI Service**:
```python
@app.post("/run")
def run(location: str = None):
    # Process and return HTTP response
    return {"status": "success"}
```

### **Cloud Run Job**:
```python
def main():
    # Process and exit
    print("Job completed")
    sys.exit(0)  # Success

if __name__ == "__main__":
    main()
```

### **Cloud Function**:
```python
@functions_framework.http
def weather_ingestion(request):
    # Process and return HTTP response
    return {"status": "success"}
```
