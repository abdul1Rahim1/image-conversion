import os
from dotenv import load_dotenv

load_dotenv()

SERVICE_API_KEY = os.getenv("SERVICE_API_KEY", "")
CATALOG_PATH = os.getenv("CATALOG_PATH", "sample_products.json")
CACHE_DB_PATH = os.getenv("CACHE_DB_PATH", "cache.sqlite")
ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()
]
