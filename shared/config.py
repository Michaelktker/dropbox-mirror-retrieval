"""
Central configuration — all values come from environment variables.

Required at runtime (Cloud Run Jobs inject these):
  GCP_PROJECT_ID, GCS_BUCKET_NAME,
  DROPBOX_APP_KEY, DROPBOX_APP_SECRET, DROPBOX_REFRESH_TOKEN

Required after infra provisioning:
  VECTOR_SEARCH_INDEX_ID, VECTOR_SEARCH_ENDPOINT_ID,
  VECTOR_SEARCH_DEPLOYED_INDEX_ID,
  VERTEX_SEARCH_DATASTORE_ID, VERTEX_SEARCH_ENGINE_ID
"""

import os


def _require(name: str) -> str:
    """Return env-var value or raise with a clear message."""
    val = os.environ.get(name)
    if not val:
        raise EnvironmentError(
            f"Missing required environment variable: {name}"
        )
    return val


def _optional(name: str, default: str) -> str:
    return os.environ.get(name, default)


# ── Google Cloud ──────────────────────────────────────────────
GCP_PROJECT_ID: str = _require("GCP_PROJECT_ID")
GCP_REGION: str = _optional("GCP_REGION", "us-central1")
GCS_BUCKET_NAME: str = _require("GCS_BUCKET_NAME")

# ── Dropbox (OAuth2 refresh-token flow) ──────────────────────
DROPBOX_APP_KEY: str = _require("DROPBOX_APP_KEY")
DROPBOX_APP_SECRET: str = _require("DROPBOX_APP_SECRET")
DROPBOX_REFRESH_TOKEN: str = _require("DROPBOX_REFRESH_TOKEN")

# ── Vertex AI Vector Search (set after infra creation) ───────
VECTOR_SEARCH_INDEX_ID: str = _optional("VECTOR_SEARCH_INDEX_ID", "")
VECTOR_SEARCH_ENDPOINT_ID: str = _optional("VECTOR_SEARCH_ENDPOINT_ID", "")
VECTOR_SEARCH_DEPLOYED_INDEX_ID: str = _optional(
    "VECTOR_SEARCH_DEPLOYED_INDEX_ID", ""
)

# ── Vertex AI Search / Discovery Engine ──────────────────────
VERTEX_SEARCH_DATASTORE_ID: str = _optional("VERTEX_SEARCH_DATASTORE_ID", "")
VERTEX_SEARCH_ENGINE_ID: str = _optional("VERTEX_SEARCH_ENGINE_ID", "")

# ── GCS prefixes (constants) ─────────────────────────────────
GCS_PREFIX_IMAGES = "mirror/images/"
GCS_PREFIX_DOCS = "mirror/docs/"
GCS_PREFIX_MEDIA = "mirror/media/"
GCS_PREFIX_META = "mirror/meta/"
GCS_PREFIX_STATE = "mirror/state/"

SYNC_STATE_KEY = "mirror/state/sync_state.json"
PATH_INDEX_KEY = "mirror/state/path_index.json"
REV_INDEX_KEY = "mirror/state/rev_index.json"
EMBEDDING_STATE_KEY = "mirror/state/embedding_state.json"

# ── Embedding model ──────────────────────────────────────────
EMBEDDING_MODEL_NAME = "multimodalembedding@001"
EMBEDDING_DIMENSION = 1408
