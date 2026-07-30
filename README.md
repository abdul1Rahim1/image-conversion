# Product Image Variation Pipeline

Take a CSV/JSON of products, generate 2–3 AI-edited variants of each product image (same product, new angle/lighting/background), scrub and randomize EXIF, rename, re-encode to WebP, upload to your S3-compatible bucket (Cloudflare R2, AWS S3, ...), rewrite the title + description via Claude, and emit an updated CSV with fresh URLs. No trace of the original image or copy is preserved.

## Pipeline

```
CSV/JSON  ─►  download  ─►  AI image edit (N variants)  ─►  scrub + randomize EXIF
                                                         ─►  re-encode WebP
                                                         ─►  rename (uuid) + upload
                                                         ─►  rewrite title/description (Claude)
                                                         ─►  output CSV
```

## Install

```
pip install -r requirements.txt
cp .env.example .env
# fill in .env
```

## Run

```
python run.py sample_products.csv out/products_new.csv
```

The output file is append-only and checkpointed by `id`: killing and restarting resumes where it left off.

## Configuration

Everything in `.env`. Key knobs:

- `IMAGE_PROVIDER` — `openai` (gpt-image-1) or `replicate` (Flux Kontext)
- `VARIATIONS_PER_IMAGE` — default 3
- `CONCURRENCY` — default 4 products in flight
- `REWRITE_COPY` — set `false` to skip Claude rewrites
- `COL_ID` / `COL_TITLE` / `COL_DESCRIPTION` / `COL_IMAGE_URL` — map your input columns

## Input formats

**CSV** (header row required):

```
id,title,description,image_url
SKU-001,...,...,https://...
```

**JSON** — either a list of objects or `{"products": [...]}`.

## Output

```
id,title,description,image_url,variant_1_url,variant_2_url,variant_3_url,error
SKU-001,<rewritten>,<rewritten>,<original>,https://cdn.../uuid-v1.webp,...,...,
```

Failed rows are still written with the `error` column populated so you can retry them.

## What gets erased

- Original EXIF (make/model, timestamps, GPS, software, thumbnail, comments) — nuked by re-encoding
- Filename — regenerated as `products/<slug>/<uuid>-vN.webp`
- Perceptual similarity — the image is regenerated, not just re-encoded
- Copy — rewritten with different structure/wording, facts preserved

## What gets injected

- Fake but plausible EXIF (random camera make/model, lens, aperture, ISO, timestamp within the last 6 months, no GPS)
- New URL path with no relationship to the source

## Layout

```
src/
├── config.py            # .env loader
├── prompts.py           # edit prompts + rewrite system prompt
├── io_utils.py          # CSV/JSON load, checkpointed output, http download
├── metadata.py          # scrub + randomize EXIF, re-encode
├── image_variations.py  # pluggable OpenAI / Replicate provider
├── storage.py           # S3-compatible upload
├── content_rewrite.py   # Claude-based title/desc rewriter
└── pipeline.py          # orchestrator
run.py                   # CLI
```
