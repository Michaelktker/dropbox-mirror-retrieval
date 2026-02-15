"""
Chunked/streaming download for large Dropbox files.

Uses iter_content to avoid holding the entire file in memory at once.
Suitable for files up to ~10 GB.
"""

import logging
from pathlib import Path

import dropbox

logger = logging.getLogger(__name__)

CHUNK_SIZE = 8 * 1024 * 1024  # 8 MiB per chunk


def download_large_file(
    dbx: dropbox.Dropbox,
    dropbox_path: str,
    local_path: str | Path,
) -> int:
    """Download a large file from Dropbox via streaming to disk.

    Returns the total number of bytes downloaded.
    """
    local_path = Path(local_path)
    local_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Starting chunked download: %s → %s", dropbox_path, local_path)
    _md, response = dbx.files_download(dropbox_path)

    total = 0
    with open(local_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
            if chunk:
                f.write(chunk)
                total += len(chunk)

    logger.info(
        "Downloaded %s (%.2f GB) → %s",
        dropbox_path,
        total / (1024**3),
        local_path,
    )
    return total
