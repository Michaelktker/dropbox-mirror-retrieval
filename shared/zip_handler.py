"""
Disk-based streaming ZIP extraction for large archives (5–10 GB+).

Extracts one file at a time to keep memory usage constant.
Caller is responsible for deleting each yielded file's local_path
after upload to free disk space.
"""

import os
import zipfile
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)

SCRATCH_DIR = Path(os.environ.get("SCRATCH_DIR", "/scratch"))

# Skip individual files larger than 1 GB inside the ZIP
MAX_INNER_FILE_SIZE = 1 * 1024 * 1024 * 1024

# Read buffer for extraction (8 MiB)
_READ_BUF = 8 * 1024 * 1024


@dataclass
class ExtractedFile:
    """Represents a single file extracted from a ZIP archive."""

    original_zip_path: str  # Dropbox path of the ZIP
    inner_path: str  # path inside the ZIP
    filename: str  # just the filename
    local_path: Path  # temp file on disk — caller must delete
    size: int  # file size in bytes


def extract_zip_streaming(
    zip_path: Path,
    zip_dropbox_path: str,
) -> Iterator[ExtractedFile]:
    """Yield one ExtractedFile at a time from a ZIP on disk.

    Each yielded file exists at ``local_path``.  The caller is responsible
    for deleting it after upload to free disk space.

    Memory usage is constant regardless of ZIP size.
    """
    extract_dir = SCRATCH_DIR / "zip_extract"
    extract_dir.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path) as zf:
            entries = [
                info
                for info in zf.infolist()
                if not info.is_dir()
                and not info.filename.startswith("__MACOSX")
                and not info.filename.rsplit("/", 1)[-1].startswith(".")
            ]
            logger.info(
                "ZIP %s contains %d extractable files (archive: %.2f GB)",
                zip_dropbox_path,
                len(entries),
                zip_path.stat().st_size / (1024**3),
            )

            for info in entries:
                basename = info.filename.rsplit("/", 1)[-1]

                if info.file_size > MAX_INNER_FILE_SIZE:
                    logger.warning(
                        "Skipping oversized file in ZIP: %s (%.1f GB)",
                        info.filename,
                        info.file_size / (1024**3),
                    )
                    continue

                # Extract single file to disk with a safe name
                safe_name = info.filename.replace("/", "_")
                out_path = extract_dir / safe_name
                try:
                    with zf.open(info) as src, open(out_path, "wb") as dst:
                        while True:
                            chunk = src.read(_READ_BUF)
                            if not chunk:
                                break
                            dst.write(chunk)

                    yield ExtractedFile(
                        original_zip_path=zip_dropbox_path,
                        inner_path=info.filename,
                        filename=basename,
                        local_path=out_path,
                        size=info.file_size,
                    )
                except Exception:
                    logger.exception(
                        "Failed to extract: %s from %s",
                        info.filename,
                        zip_dropbox_path,
                    )
                    # Clean up partial file
                    if out_path.exists():
                        out_path.unlink(missing_ok=True)

    except zipfile.BadZipFile:
        logger.warning("Corrupt or invalid ZIP: %s", zip_dropbox_path)
    except Exception:
        logger.exception("Failed to process ZIP: %s", zip_dropbox_path)
