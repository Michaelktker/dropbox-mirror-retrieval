"""
Job A — Sync Dropbox → GCS mirror.

Behaviour:
  1. Read saved cursor from GCS (or None on first run).
  2. Baseline crawl (no cursor) or incremental sync (has cursor).
  3. For each FileMetadata  → download, upload to mirror/<cat>/<id>, write meta JSON.
     For each DeletedMetadata → remove blob + meta, update path index.
  4. Persist new cursor + path index to GCS.
"""

import logging
import sys

# ── make `shared` importable when running from repo root ──
sys.path.insert(0, "/app")  # Docker layout
sys.path.insert(0, ".")     # local dev

from shared import config  # noqa: E402
from shared.categories import categorize, gcs_key, meta_key, mime_type  # noqa: E402
from shared.dropbox_client import DropboxClient  # noqa: E402
from shared.gcs import (  # noqa: E402
    delete_blob,
    list_blobs,
    read_json,
    upload_bytes,
    write_json,
)

from dropbox.files import DeletedMetadata, FileMetadata, FolderMetadata  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger(__name__)

BUCKET = config.GCS_BUCKET_NAME

# Size limit: skip files larger than 150 MB (Dropbox SDK download limit)
MAX_FILE_SIZE = 150 * 1024 * 1024

# Save state every N files to survive timeouts
SAVE_INTERVAL = 100


def _clean_file_id(raw_id: str) -> str:
    """Strip the 'id:' prefix Dropbox uses, keep alphanumeric ID."""
    return raw_id.replace("id:", "") if raw_id else raw_id


def run() -> None:
    """Main sync logic."""
    dbx = DropboxClient(
        app_key=config.DROPBOX_APP_KEY,
        app_secret=config.DROPBOX_APP_SECRET,
        refresh_token=config.DROPBOX_REFRESH_TOKEN,
    )

    # ── Load state ────────────────────────────────────────
    sync_state = read_json(BUCKET, config.SYNC_STATE_KEY)
    path_index: dict[str, str] = read_json(BUCKET, config.PATH_INDEX_KEY)
    rev_index: dict[str, str] = read_json(BUCKET, config.REV_INDEX_KEY) or {}
    # path_index: { dropbox_path_lower: file_id }
    # rev_index: { file_id: rev } — tracks synced revisions to skip unchanged files

    # ── Rebuild rev_index from existing metadata (migration) ──
    if not rev_index:
        logger.info("Rebuilding rev_index from existing metadata...")
        meta_keys = list_blobs(BUCKET, config.GCS_PREFIX_META)
        for mkey in meta_keys:
            if mkey.endswith(".json"):
                meta = read_json(BUCKET, mkey)
                fid = meta.get("dropbox_file_id")
                rev = meta.get("rev")
                if fid and rev:
                    rev_index[fid] = rev
        if rev_index:
            write_json(BUCKET, config.REV_INDEX_KEY, rev_index)
            logger.info("Rebuilt rev_index with %d entries", len(rev_index))

    saved_cursor = sync_state.get("cursor")

    # ── List entries ──────────────────────────────────────
    if saved_cursor:
        logger.info("Incremental sync from saved cursor")
        entries, new_cursor = dbx.list_changes(saved_cursor)
    else:
        logger.info("Baseline crawl (no cursor found)")
        entries, new_cursor = dbx.list_all("")

    # ── Process entries ───────────────────────────────────
    stats = {"synced": 0, "deleted": 0, "skipped": 0, "unchanged": 0}
    total_processed = 0

    def save_state_checkpoint():
        """Save state periodically to survive timeouts."""
        write_json(BUCKET, config.PATH_INDEX_KEY, path_index)
        write_json(BUCKET, config.REV_INDEX_KEY, rev_index)
        logger.info("Checkpoint saved: %d processed so far", total_processed)

    for entry in entries:
        # — Folders: skip —
        if isinstance(entry, FolderMetadata):
            continue

        # — Deletions —
        if isinstance(entry, DeletedMetadata):
            path_lower = entry.path_lower
            file_id = path_index.get(path_lower)
            if not file_id:
                logger.debug("Delete: no index entry for %s", path_lower)
                stats["skipped"] += 1
                continue

            # Determine category from meta (if exists)
            meta = read_json(BUCKET, meta_key(file_id))
            cat = meta.get("category")
            if cat:
                delete_blob(BUCKET, gcs_key(cat, file_id))
            delete_blob(BUCKET, meta_key(file_id))
            path_index.pop(path_lower, None)
            rev_index.pop(file_id, None)
            stats["deleted"] += 1
            total_processed += 1
            logger.info("Deleted %s (id=%s)", path_lower, file_id)

            if total_processed % SAVE_INTERVAL == 0:
                save_state_checkpoint()
            continue

        # — Files —
        if isinstance(entry, FileMetadata):
            cat = categorize(entry.name)
            if cat is None:
                logger.debug("Skipping unsupported extension: %s", entry.name)
                stats["skipped"] += 1
                continue

            if entry.size > MAX_FILE_SIZE:
                logger.warning(
                    "Skipping large file (%d MB): %s",
                    entry.size // (1024 * 1024),
                    entry.path_display,
                )
                stats["skipped"] += 1
                continue

            file_id = _clean_file_id(entry.id)

            # Skip if already synced with same revision
            if rev_index.get(file_id) == entry.rev:
                stats["unchanged"] += 1
                continue

            obj_key = gcs_key(cat, file_id)

            # Download from Dropbox
            try:
                _, data = dbx.download_file(entry.path_lower)
            except Exception:
                logger.exception("Failed to download %s", entry.path_display)
                stats["skipped"] += 1
                continue

            # Upload to GCS
            content_type = mime_type(entry.name)
            gcs_uri = upload_bytes(BUCKET, obj_key, data, content_type)

            # Write metadata sidecar
            meta_obj = {
                "dropbox_file_id": file_id,
                "dropbox_path": entry.path_display,
                "rev": entry.rev,
                "mime_type": content_type,
                "size": entry.size,
                "server_modified": str(entry.server_modified),
                "category": cat,
                "gcs_uri": gcs_uri,
                "caption": entry.name,
            }
            write_json(BUCKET, meta_key(file_id), meta_obj)

            # Update indexes
            path_index[entry.path_lower] = file_id
            rev_index[file_id] = entry.rev

            stats["synced"] += 1
            total_processed += 1
            logger.info("Synced %s → %s", entry.path_display, obj_key)

            # Periodic checkpoint
            if total_processed % SAVE_INTERVAL == 0:
                save_state_checkpoint()

    # ── Persist final state ───────────────────────────────
    write_json(BUCKET, config.SYNC_STATE_KEY, {"cursor": new_cursor})
    write_json(BUCKET, config.PATH_INDEX_KEY, path_index)
    write_json(BUCKET, config.REV_INDEX_KEY, rev_index)

    logger.info(
        "Sync complete — synced=%d  deleted=%d  skipped=%d  unchanged=%d",
        stats["synced"],
        stats["deleted"],
        stats["skipped"],
        stats["unchanged"],
    )


if __name__ == "__main__":
    run()
