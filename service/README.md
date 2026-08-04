# Product Materialization Service

FastAPI wrapper around the image/copy pipeline. Runs on your Lightsail box; the WordPress plugin calls it over HTTPS.

## Endpoints

| Method | Path                       | What it does |
|--------|----------------------------|--------------|
| GET    | `/health`                  | Liveness + counts. **No auth.** |
| GET    | `/search?q=...&limit=20`   | Substring match against the catalog. Metadata only — does not generate images. |
| GET    | `/product/{asin}`          | Returns cached product if ready. If cold, kicks off materialization in the background and returns `status: "processing"`. Poll until `status: "ready"`. |
| POST   | `/materialize/{asin}`      | Blocking re-materialization (bypasses cache). Use sparingly. |

All endpoints except `/health` require `X-API-Key: <SERVICE_API_KEY>` header.

## Local run

```bash
pip install -r requirements.txt
cp .env.example .env
# fill in .env — including SERVICE_API_KEY and CATALOG_PATH
uvicorn service.main:app --host 0.0.0.0 --port 8000 --reload
```

Open http://localhost:8000/docs for the auto-generated Swagger UI. Set the `X-API-Key` header in the "Authorize" dialog.

## Try it

```bash
KEY=your-service-key
curl -s -H "X-API-Key: $KEY" 'http://localhost:8000/health' | jq
curl -s -H "X-API-Key: $KEY" 'http://localhost:8000/search?q=action%20figure' | jq
curl -s -H "X-API-Key: $KEY" 'http://localhost:8000/product/B0FV2PQ1NQ' | jq
# first call → status: processing; poll after ~60s → status: ready
```

## Lightsail deployment

See root `README.md` (patch 4 will add a step-by-step: systemd unit + Nginx reverse proxy + Let's Encrypt).
