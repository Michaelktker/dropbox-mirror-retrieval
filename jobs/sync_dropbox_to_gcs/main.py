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
import mimetypes
import os
import sys
from pathlib import Path

# ── make `shared` importable when running from repo root ──
sys.path.insert(0, "/app")  # Docker layout
sys.path.insert(0, ".")     # local dev

from shared import config  # noqa: E402
from shared.categories import categorize, gcs_key, meta_key, mime_type  # noqa: E402
from shared.dropbox_client import DropboxClient  # noqa: E402
from shared.dropbox_download import download_large_file  # noqa: E402
from shared.zip_handler import extract_zip_streaming, SCRATCH_DIR  # noqa: E402
from shared.gcs import (  # noqa: E402
    delete_blob,
    list_blobs,
    read_json,
    upload_bytes,
    upload_from_filename,
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
    stats = {"synced": 0, "deleted": 0, "skipped": 0, "unchanged": 0, "zip_extracted": 0}
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

            # ── ZIP deletion: clean up all extracted children ──
            if path_lower.endswith(".zip"):
                zip_prefix = f"{path_lower}!/"
                children_to_delete = [
                    (p, fid)
                    for p, fid in list(path_index.items())
                    if p.startswith(zip_prefix)
                ]
                for child_path, child_id in children_to_delete:
                    child_meta = read_json(BUCKET, meta_key(child_id))
                    child_cat = child_meta.get("category")
                    if child_cat:
                        child_gcs_uri = child_meta.get("gcs_uri", "")
                        child_ext = ""
                        if child_cat == "docs" and child_gcs_uri:
                            _, child_ext = os.path.splitext(child_gcs_uri)
                        delete_blob(BUCKET, gcs_key(child_cat, child_id, child_ext))
                    delete_blob(BUCKET, meta_key(child_id))
                    path_index.pop(child_path, None)
                    stats["deleted"] += 1
                    logger.info("Deleted ZIP-extracted file: %s", child_path)

                # Remove the ZIP itself from rev_index
                zip_file_id = path_index.get(path_lower)
                if zip_file_id:
                    rev_index.pop(zip_file_id, None)
                    path_index.pop(path_lower, None)
                    delete_blob(BUCKET, meta_key(zip_file_id))

                total_processed += 1
                logger.info(
                    "Deleted ZIP and %d extracted children: %s",
                    len(children_to_delete),
                    path_lower,
                )
                if total_processed % SAVE_INTERVAL == 0:
                    save_state_checkpoint()
                continue

            # ── Regular file deletion ──
            file_id = path_index.get(path_lower)
            if not file_id:
                logger.debug("Delete: no index entry for %s", path_lower)
                stats["skipped"] += 1
                continue

            # Determine category from meta (if exists)
            meta = read_json(BUCKET, meta_key(file_id))
            cat = meta.get("category")
            if cat:
                # For docs, gcs_uri includes extension; extract it
                gcs_uri = meta.get("gcs_uri", "")
                extension = ""
                if cat == "docs" and gcs_uri:
                    _, extension = os.path.splitext(gcs_uri)
                delete_blob(BUCKET, gcs_key(cat, file_id, extension))
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

            # ── ZIP file handling ──────────────────────────────
            if entry.name.lower().endswith(".zip"):
                file_id = _clean_file_id(entry.id)

                # Skip if ZIP rev unchanged
                if rev_index.get(file_id) == entry.rev:
                    stats["unchanged"] += 1
                    continue

                if entry.size > 10 * 1024 * 1024 * 1024:  # 10 GB hard limit
                    logger.warning(
                        "Skipping ZIP > 10 GB (%d GB): %s",
                        entry.size // (1024**3),
                        entry.path_display,
                    )
                    stats["skipped"] += 1
                    continue

                logger.info(
                    "ZIP detected (%.2f GB): %s",
                    (entry.size or 0) / (1024**3),
                    entry.path_display,
                )

                # Step 1: Stream-download to scratch disk
                zip_local = SCRATCH_DIR / f"{file_id}.zip"
                zip_local.parent.mkdir(parents=True, exist_ok=True)
                try:
                    download_large_file(dbx._dbx, entry.path_lower, zip_local)
                except Exception:
                    logger.exception("Failed to download ZIP: %s", entry.path_display)
                    stats["skipped"] += 1
                    continue

                # Step 2: Stream-extract and upload one file at a time
                zip_member_count = 0
                try:
                    for extracted in extract_zip_streaming(zip_local, entry.path_lower):
                        inner_cat = categorize(extracted.filename)
                        if inner_cat is None:
                            logger.debug(
                                "Skipping unsupported in ZIP: %s/%s",
                                entry.path_lower,
                                extracted.inner_path,
                            )
                            stats["skipped"] += 1
                            extracted.local_path.unlink(missing_ok=True)
                            continue

                        inner_id = (
                            f"{file_id}___{extracted.inner_path.replace('/', '_')}"
                        )

                        # Preserve file extension for docs (Vertex AI Search needs it)
                        _, ext = os.path.splitext(extracted.filename)
                        extension = ext.lower() if inner_cat == "docs" else ""
                        obj_key = gcs_key(inner_cat, inner_id, extension)

                        # Upload from disk (not memory)
                        content_type_val = mime_type(extracted.filename)
                        gcs_uri = upload_from_filename(
                            BUCKET, obj_key, str(extracted.local_path), content_type_val
                        )
                        logger.info(
                            "Uploaded ZIP member: %s (%.1f MB) → %s",
                            extracted.inner_path,
                            extracted.size / (1024 * 1024),
                            obj_key,
                        )

                        # Write metadata sidecar
                        inner_mime, _ = mimetypes.guess_type(extracted.filename)
                        meta_obj = {
                            "dropbox_file_id": inner_id,
                            "dropbox_path": f"{entry.path_lower}!/{extracted.inner_path}",
                            "rev": entry.rev,
                            "mime_type": inner_mime or "application/octet-stream",
                            "size": extracted.size,
                            "server_modified": str(entry.server_modified),
                            "category": inner_cat,
                            "gcs_uri": gcs_uri,
                            "caption": extracted.filename,
                            "source_zip": entry.path_display,
                        }
                        write_json(BUCKET, meta_key(inner_id), meta_obj)

                        # Update path_index for this extracted file
                        synthetic_path = f"{entry.path_lower}!/{extracted.inner_path}"
                        path_index[synthetic_path] = inner_id

                        zip_member_count += 1
                        stats["zip_extracted"] += 1

                        # Delete temp file immediately to free disk
                        extracted.local_path.unlink(missing_ok=True)

                finally:
                    # Always clean up the downloaded ZIP
                    zip_local.unlink(missing_ok=True)
                    logger.info(
                        "ZIP done: %d files extracted from %s",
                        zip_member_count,
                        entry.path_display,
                    )

                # Track the ZIP itself so we skip it next run
                path_index[entry.path_lower] = file_id
                rev_index[file_id] = entry.rev

                # Write a thin meta sidecar for the ZIP itself (for deletion tracking)
                zip_meta = {
                    "dropbox_file_id": file_id,
                    "dropbox_path": entry.path_display,
                    "rev": entry.rev,
                    "category": "archive",
                    "size": entry.size,
                    "server_modified": str(entry.server_modified),
                    "extracted_count": zip_member_count,
                }
                write_json(BUCKET, meta_key(file_id), zip_meta)

                total_processed += 1
                if total_processed % SAVE_INTERVAL == 0:
                    save_state_checkpoint()
                continue

            # ── Regular file handling ──────────────────────────
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

            # For docs, include file extension so Vertex AI Search can detect type
            _, ext = os.path.splitext(entry.name)
            extension = ext.lower() if cat == "docs" else ""
            obj_key = gcs_key(cat, file_id, extension)

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
        "Sync complete — synced=%d  deleted=%d  skipped=%d  unchanged=%d  zip_extracted=%d",
        stats["synced"],
        stats["deleted"],
        stats["skipped"],
        stats["unchanged"],
        stats["zip_extracted"],
    )


if __name__ == "__main__":
    run()
