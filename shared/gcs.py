"""
Thin wrapper around google-cloud-storage for mirror operations.
"""

import json
import logging
from typing import Any, Optional

from google.cloud import storage

logger = logging.getLogger(__name__)

# Module-level client (lazy-initialised)
_client: Optional[storage.Client] = None


def _get_client() -> storage.Client:
    global _client
    if _client is None:
        _client = storage.Client()
    return _client


def _bucket(bucket_name: str) -> storage.Bucket:
    return _get_client().bucket(bucket_name)


# ── Upload / Download ────────────────────────────────────────


def upload_bytes(
    bucket_name: str,
    key: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> str:
    """Upload raw bytes to GCS. Returns the gs:// URI."""
    blob = _bucket(bucket_name).blob(key)
    blob.upload_from_string(data, content_type=content_type)
    uri = f"gs://{bucket_name}/{key}"
    logger.debug("Uploaded %s (%d bytes)", uri, len(data))
    return uri


def upload_from_filename(
    bucket_name: str,
    key: str,
    local_path: str,
    content_type: str = "application/octet-stream",
    timeout: int = 600,
) -> str:
    """Upload a local file to GCS by path (avoids loading into memory).

    Returns the gs:// URI.
    """
    blob = _bucket(bucket_name).blob(key)
    blob.upload_from_filename(local_path, content_type=content_type, timeout=timeout)
    uri = f"gs://{bucket_name}/{key}"
    logger.debug("Uploaded %s from %s", uri, local_path)
    return uri


def download_bytes(bucket_name: str, key: str) -> bytes:
    """Download a blob as bytes."""
    blob = _bucket(bucket_name).blob(key)
    return blob.download_as_bytes()


def get_blob_size(bucket_name: str, key: str) -> int:
    """Get the size of a blob in bytes. Returns 0 if blob doesn't exist."""
    blob = _bucket(bucket_name).blob(key)
    blob.reload()  # Fetch metadata from GCS
    return blob.size or 0


# ── Delete ───────────────────────────────────────────────────


def delete_blob(bucket_name: str, key: str) -> None:
    """Delete a single blob; no error if it doesn't exist."""
    blob = _bucket(bucket_name).blob(key)
    try:
        blob.delete()
        logger.debug("Deleted gs://%s/%s", bucket_name, key)
    except Exception:
        logger.debug("Blob gs://%s/%s not found (already deleted?)", bucket_name, key)


# ── JSON helpers ─────────────────────────────────────────────


def read_json(bucket_name: str, key: str) -> dict[str, Any]:
    """Download a JSON blob and parse it. Returns {} if the blob doesn't exist."""
    blob = _bucket(bucket_name).blob(key)
    if not blob.exists():
        return {}
    raw = blob.download_as_bytes()
    return json.loads(raw)


def write_json(bucket_name: str, key: str, obj: Any) -> None:
    """Serialise *obj* as JSON and upload."""
    data = json.dumps(obj, indent=2, default=str).encode()
    upload_bytes(bucket_name, key, data, content_type="application/json")


# ── Listing ──────────────────────────────────────────────────


def list_blobs(bucket_name: str, prefix: str) -> list[str]:
    """Return a list of blob names (keys) under *prefix*."""
    blobs = _get_client().list_blobs(bucket_name, prefix=prefix)
    return [b.name for b in blobs]


def blob_exists(bucket_name: str, key: str) -> bool:
    return _bucket(bucket_name).blob(key).exists()
