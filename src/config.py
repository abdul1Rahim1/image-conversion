import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _get(name: str, default: str | None = None, required: bool = False) -> str:
    v = os.getenv(name, default)
    if required and not v:
        raise RuntimeError(f"Missing required env var: {name}")
    return v or ""


@dataclass(frozen=True)
class Config:
    image_provider: str = _get("IMAGE_PROVIDER", "openai")

    openai_api_key: str = _get("OPENAI_API_KEY", "")
    openai_image_model: str = _get("OPENAI_IMAGE_MODEL", "gpt-image-1")
    openai_image_size: str = _get("OPENAI_IMAGE_SIZE", "1024x1024")
    openai_image_quality: str = _get("OPENAI_IMAGE_QUALITY", "high")

    replicate_api_token: str = _get("REPLICATE_API_TOKEN", "")
    replicate_model: str = _get("REPLICATE_MODEL", "black-forest-labs/flux-kontext-pro")

    anthropic_api_key: str = _get("ANTHROPIC_API_KEY", "")
    anthropic_model: str = _get("ANTHROPIC_MODEL", "claude-opus-4-7")
    rewrite_copy: bool = _get("REWRITE_COPY", "true").lower() == "true"

    s3_endpoint_url: str = _get("S3_ENDPOINT_URL", "")
    s3_access_key_id: str = _get("S3_ACCESS_KEY_ID", "")
    s3_secret_access_key: str = _get("S3_SECRET_ACCESS_KEY", "")
    s3_bucket: str = _get("S3_BUCKET", "")
    s3_region: str = _get("S3_REGION", "auto")
    public_base_url: str = _get("PUBLIC_BASE_URL", "").rstrip("/")

    variations_per_image: int = int(_get("VARIATIONS_PER_IMAGE", "3"))
    concurrency: int = int(_get("CONCURRENCY", "4"))
    output_format: str = _get("OUTPUT_FORMAT", "webp").lower()
    output_quality: int = int(_get("OUTPUT_QUALITY", "85"))

    col_id: str = _get("COL_ID", "id")
    col_title: str = _get("COL_TITLE", "title")
    col_description: str = _get("COL_DESCRIPTION", "description")
    col_image_url: str = _get("COL_IMAGE_URL", "image_url")


CFG = Config()
