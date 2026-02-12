"""
Job B — Generate multimodal embeddings for images and upsert to Vector Search.

Behaviour:
  1. Load embedding_state.json from GCS (file_id → embedded_rev).
  2. Scan all mirror/meta/*.json for category=="images".
  3. For new/changed images: embed via multimodalembedding@001, upsert datapoint.
  4. For stale IDs (image deleted): remove datapoints.
  5. Persist updated embedding_state.json.
"""

import logging
import sys

sys.path.insert(0, "/app")
sys.path.insert(0, ".")

import vertexai  # noqa: E402
from google.cloud import aiplatform  # noqa: E402
from google.cloud.aiplatform_v1.types import index as index_types  # noqa: E402
from vertexai.vision_models import Image, MultiModalEmbeddingModel  # noqa: E402

from shared import config  # noqa: E402
from shared.gcs import (  # noqa: E402
    download_bytes,
    get_blob_size,
    list_blobs,
    read_json,
    write_json,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger(__name__)

BUCKET = config.GCS_BUCKET_NAME

# Vertex AI multimodal embedding has a 27MB base64 string limit.
# Base64 adds ~33% overhead, so we limit raw file size to 20MB.
MAX_IMAGE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB


def run() -> None:
    """Main embedding logic."""

    # ── Validate required config ──────────────────────────
    if not config.VECTOR_SEARCH_INDEX_ID:
        logger.error("VECTOR_SEARCH_INDEX_ID not set — run infra scripts first")
        sys.exit(1)

    # ── Init Vertex AI ────────────────────────────────────
    vertexai.init(project=config.GCP_PROJECT_ID, location=config.GCP_REGION)
    aiplatform.init(project=config.GCP_PROJECT_ID, location=config.GCP_REGION)

    model = MultiModalEmbeddingModel.from_pretrained(config.EMBEDDING_MODEL_NAME)

    index_resource = (
        f"projects/{config.GCP_PROJECT_ID}"
        f"/locations/{config.GCP_REGION}"
        f"/indexes/{config.VECTOR_SEARCH_INDEX_ID}"
    )
    vs_index = aiplatform.MatchingEngineIndex(index_name=index_resource)

    # ── Load state ────────────────────────────────────────
    embedding_state: dict[str, str] = read_json(BUCKET, config.EMBEDDING_STATE_KEY)
    # { file_id: rev }

    # ── Scan metadata blobs ───────────────────────────────
    meta_keys = list_blobs(BUCKET, config.GCS_PREFIX_META)
    current_image_ids: set[str] = set()

    stats = {"embedded": 0, "skipped": 0, "removed": 0, "errors": 0}
    checkpoint_interval = 50  # Save state every N embeddings to survive timeouts
    embeddings_since_checkpoint = 0

    for mk in meta_keys:
        if not mk.endswith(".json"):
            continue

        meta = read_json(BUCKET, mk)
        if meta.get("category") != "images":
            continue

        file_id = meta["dropbox_file_id"]
        rev = meta["rev"]
        current_image_ids.add(file_id)

        # Already embedded at this rev?
        if embedding_state.get(file_id) == rev:
            stats["skipped"] += 1
            continue

        # ── Check file size before downloading ─────────
        image_key = f"{config.GCS_PREFIX_IMAGES}{file_id}"
        try:
            file_size = get_blob_size(BUCKET, image_key)
        except Exception:
            file_size = 0

        if file_size > MAX_IMAGE_SIZE_BYTES:
            logger.info(
                "Skipping %s — size %d MB exceeds 20 MB limit",
                meta.get("caption", file_id),
                file_size // (1024 * 1024),
            )
            stats["skipped"] += 1
            continue

        # ── Embed ─────────────────────────────────────────
        try:
            gcs_uri = meta["gcs_uri"]
            image_bytes = download_bytes(BUCKET, image_key)
            image = Image(image_bytes=image_bytes)

            response = model.get_embeddings(
                image=image,
                dimension=config.EMBEDDING_DIMENSION,
            )
            vector = response.image_embedding

            if not vector:
                logger.warning("Empty embedding for %s — skipping", file_id)
                stats["errors"] += 1
                continue

            # ── Upsert datapoint ──────────────────────────
            datapoint = index_types.IndexDatapoint(
                datapoint_id=file_id,
                feature_vector=vector,
                restricts=[
                    index_types.IndexDatapoint.Restriction(
                        namespace="category",
                        allow_list=["images"],
                    ),
                ],
            )
            vs_index.upsert_datapoints(datapoints=[datapoint])

            embedding_state[file_id] = rev
            stats["embedded"] += 1
            embeddings_since_checkpoint += 1
            logger.info("Embedded %s (rev=%s)", meta.get("caption", file_id), rev)

            # ── Checkpoint save to survive timeouts ───────
            if embeddings_since_checkpoint >= checkpoint_interval:
                write_json(BUCKET, config.EMBEDDING_STATE_KEY, embedding_state)
                logger.info(
                    "Checkpoint saved — embedded=%d  skipped=%d so far",
                    stats["embedded"],
                    stats["skipped"],
                )
                embeddings_since_checkpoint = 0

        except Exception:
            logger.exception("Failed to embed %s", file_id)
            stats["errors"] += 1

    # ── Remove stale datapoints ───────────────────────────
    stale_ids = set(embedding_state.keys()) - current_image_ids
    if stale_ids:
        try:
            vs_index.remove_datapoints(datapoint_ids=list(stale_ids))
            for sid in stale_ids:
                embedding_state.pop(sid, None)
            stats["removed"] += len(stale_ids)
            logger.info("Removed %d stale datapoints", len(stale_ids))
        except Exception:
            logger.exception("Failed to remove stale datapoints")

    # ── Persist state ─────────────────────────────────────
    write_json(BUCKET, config.EMBEDDING_STATE_KEY, embedding_state)

    logger.info(
        "Embedding complete — embedded=%d  skipped=%d  removed=%d  errors=%d",
        stats["embedded"],
        stats["skipped"],
        stats["removed"],
        stats["errors"],
    )


if __name__ == "__main__":
    run()
