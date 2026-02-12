"""
File-extension → category mapping and GCS prefix helpers.

Categories:
  images  — bmp gif jpg jpeg png
  docs    — pdf docx xlsx pptx txt html
  media   — mp3 wav mp4 mov
"""

import os
from typing import Optional

CATEGORY_MAP: dict[str, set[str]] = {
    "images": {".bmp", ".gif", ".jpg", ".jpeg", ".png"},
    "docs": {".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".html"},
    "media": {".mp3", ".wav", ".mp4", ".mov"},
}

_EXT_TO_CATEGORY: dict[str, str] = {
    ext: cat for cat, exts in CATEGORY_MAP.items() for ext in exts
}

GCS_PREFIXES: dict[str, str] = {
    "images": "mirror/images/",
    "docs": "mirror/docs/",
    "media": "mirror/media/",
}

# Rough MIME-type mapping for upload content-type headers
_EXT_TO_MIME: dict[str, str] = {
    ".bmp": "image/bmp",
    ".gif": "image/gif",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".txt": "text/plain",
    ".html": "text/html",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
}


def categorize(filename: str) -> Optional[str]:
    """Return 'images', 'docs', 'media', or None for unsupported extensions."""
    _, ext = os.path.splitext(filename)
    return _EXT_TO_CATEGORY.get(ext.lower())


def gcs_prefix(category: str) -> str:
    """Return the GCS prefix for a category (e.g. 'mirror/images/')."""
    return GCS_PREFIXES[category]


def gcs_key(category: str, file_id: str, extension: str = "") -> str:
    """Full GCS object key: mirror/<category>/<file_id>[.ext].
    
    For docs, include the extension so Vertex AI Search can detect file type.
    For images/media, extension is optional (embedding uses raw bytes).
    """
    return f"{gcs_prefix(category)}{file_id}{extension}"


def meta_key(file_id: str) -> str:
    """GCS key for the metadata JSON sidecar."""
    return f"mirror/meta/{file_id}.json"


def mime_type(filename: str) -> str:
    """Best-effort MIME type from extension; falls back to octet-stream."""
    _, ext = os.path.splitext(filename)
    return _EXT_TO_MIME.get(ext.lower(), "application/octet-stream")
