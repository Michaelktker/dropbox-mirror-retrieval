"""
Vertex AI Search (Discovery Engine) helpers for importing documents.
"""

import json
import logging
import urllib.request
import urllib.error

from shared import config

logger = logging.getLogger(__name__)

# Discovery Engine API base URL
DISCOVERY_ENGINE_BASE = "https://discoveryengine.googleapis.com/v1"


def get_access_token() -> str:
    """Get GCP access token from metadata server (Cloud Run) or gcloud (local)."""
    # Try metadata server first (Cloud Run environment)
    try:
        req = urllib.request.Request(
            "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
            headers={"Metadata-Flavor": "Google"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return data["access_token"]
    except Exception:
        pass

    # Fall back to gcloud CLI (local development)
    import subprocess

    result = subprocess.run(
        ["gcloud", "auth", "print-access-token"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return result.stdout.strip()

    raise RuntimeError("Could not obtain GCP access token")


def import_document(gcs_uri: str, document_id: str) -> bool:
    """
    Import a single document from GCS to Vertex AI Search.

    Args:
        gcs_uri: Full GCS URI (e.g., gs://bucket/mirror/docs/file.pdf)
        document_id: Unique document ID for Vertex AI Search

    Returns:
        True if import succeeded, False otherwise
    """
    datastore_id = config.VERTEX_SEARCH_DATASTORE_ID
    if not datastore_id:
        logger.warning("VERTEX_SEARCH_DATASTORE_ID not set, skipping import")
        return False

    token = get_access_token()

    url = f"{DISCOVERY_ENGINE_BASE}/projects/{config.GCP_PROJECT_ID}/locations/global/collections/default_collection/dataStores/{datastore_id}/branches/default_branch/documents:import"

    payload = {
        "gcsSource": {
            "inputUris": [gcs_uri],
            "dataSchema": "content",
        },
        "reconciliationMode": "INCREMENTAL",
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "x-goog-user-project": config.GCP_PROJECT_ID,
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())

            # Check if operation completed
            if result.get("done") is False:
                # Async operation started - this is normal
                op_name = result.get("name", "")
                logger.debug("Import operation started: %s", op_name)
                return True

            # Check for errors in response
            if "error" in result:
                logger.warning(
                    "Import failed for %s: %s", gcs_uri, result["error"].get("message")
                )
                return False

            return True

    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        logger.warning("Import HTTP error for %s: %s - %s", gcs_uri, e.code, error_body)
        return False
    except Exception as e:
        logger.warning("Import failed for %s: %s", gcs_uri, e)
        return False


def import_documents_batch(gcs_uris: list[str]) -> tuple[int, int]:
    """
    Import multiple documents from GCS to Vertex AI Search in a single API call.

    Args:
        gcs_uris: List of GCS URIs (max 50 recommended)

    Returns:
        Tuple of (success_count, failure_count)
    """
    if not gcs_uris:
        return 0, 0

    datastore_id = config.VERTEX_SEARCH_DATASTORE_ID
    if not datastore_id:
        logger.warning("VERTEX_SEARCH_DATASTORE_ID not set, skipping import")
        return 0, len(gcs_uris)

    token = get_access_token()

    url = f"{DISCOVERY_ENGINE_BASE}/projects/{config.GCP_PROJECT_ID}/locations/global/collections/default_collection/dataStores/{datastore_id}/branches/default_branch/documents:import"

    payload = {
        "gcsSource": {
            "inputUris": gcs_uris,
            "dataSchema": "content",
        },
        "reconciliationMode": "INCREMENTAL",
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "x-goog-user-project": config.GCP_PROJECT_ID,
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode())

            # Check if operation completed
            if result.get("done") is False:
                # Async operation started - this is normal
                op_name = result.get("name", "")
                logger.debug("Batch import operation started: %s", op_name)
                return len(gcs_uris), 0

            # Check for errors in response
            if "error" in result:
                logger.warning(
                    "Batch import failed for %d docs: %s",
                    len(gcs_uris),
                    result["error"].get("message"),
                )
                return 0, len(gcs_uris)

            # Check metadata for partial success
            metadata = result.get("metadata", {})
            success = int(metadata.get("successCount", len(gcs_uris)))
            failed = int(metadata.get("failureCount", 0))
            logger.info("Batch import: %d success, %d failed", success, failed)
            return success, failed

    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        logger.warning("Batch import HTTP error: %s - %s", e.code, error_body)
        return 0, len(gcs_uris)
    except Exception as e:
        logger.warning("Batch import failed: %s", e)
        return 0, len(gcs_uris)


# Recommended batch size for Vertex AI Search imports
BATCH_SIZE = 50


class DocImportBuffer:
    """
    Buffer for batching document imports to Vertex AI Search.

    Usage:
        buffer = DocImportBuffer()
        buffer.add(gcs_uri)  # Adds to buffer
        buffer.add(gcs_uri)  # Adds to buffer
        ...
        buffer.flush()  # Imports any remaining docs
    """

    def __init__(self):
        self._uris: list[str] = []
        self.total_success = 0
        self.total_failed = 0

    def add(self, gcs_uri: str) -> None:
        """Add a doc URI to the buffer, flushing if batch is full."""
        self._uris.append(gcs_uri)
        if len(self._uris) >= BATCH_SIZE:
            self.flush()

    def flush(self) -> None:
        """Import all buffered docs and clear the buffer."""
        if not self._uris:
            return

        logger.info("Importing batch of %d docs to Vertex AI Search...", len(self._uris))
        success, failed = import_documents_batch(self._uris)
        self.total_success += success
        self.total_failed += failed
        self._uris = []

        if failed > 0:
            logger.warning("Batch had %d failures", failed)

    def get_stats(self) -> tuple[int, int]:
        """Returns (total_success, total_failed). Flushes any remaining first."""
        self.flush()
        return self.total_success, self.total_failed
