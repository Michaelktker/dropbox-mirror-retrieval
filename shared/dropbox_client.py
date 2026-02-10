"""
Dropbox SDK wrapper — OAuth2 refresh-token flow.

Provides helpers for:
  - cursor-based folder listing (baseline + incremental)
  - file download with proper resource cleanup
"""

import contextlib
import logging
from typing import Optional

import dropbox
from dropbox.files import (
    DeletedMetadata,
    FileMetadata,
    FolderMetadata,
    ListFolderResult,
    Metadata,
)

logger = logging.getLogger(__name__)


class DropboxClient:
    """Light wrapper around the official Dropbox SDK."""

    def __init__(
        self,
        app_key: str,
        app_secret: str,
        refresh_token: str,
    ) -> None:
        self._dbx = dropbox.Dropbox(
            oauth2_refresh_token=refresh_token,
            app_key=app_key,
            app_secret=app_secret,
        )
        logger.info("Dropbox client initialised (refresh-token flow)")

    # ── Listing ──────────────────────────────────────────────

    def list_all(
        self,
        path: str = "",
        recursive: bool = True,
        include_deleted: bool = True,
    ) -> tuple[list[Metadata], str]:
        """
        Full recursive listing from *path* ('' = root).
        Returns (entries, cursor).
        """
        result: ListFolderResult = self._dbx.files_list_folder(
            path,
            recursive=recursive,
            include_deleted=include_deleted,
        )
        entries: list[Metadata] = list(result.entries)

        while result.has_more:
            result = self._dbx.files_list_folder_continue(result.cursor)
            entries.extend(result.entries)

        logger.info(
            "Baseline listing: %d entries, cursor=%s…",
            len(entries),
            result.cursor[:20],
        )
        return entries, result.cursor

    def list_changes(
        self, cursor: str
    ) -> tuple[list[Metadata], str]:
        """
        Incremental change listing from a saved cursor.
        Returns (entries, new_cursor).
        """
        entries: list[Metadata] = []
        result: ListFolderResult = self._dbx.files_list_folder_continue(cursor)
        entries.extend(result.entries)

        while result.has_more:
            result = self._dbx.files_list_folder_continue(result.cursor)
            entries.extend(result.entries)

        logger.info(
            "Incremental listing: %d changes, cursor=%s…",
            len(entries),
            result.cursor[:20],
        )
        return entries, result.cursor

    # ── Download ─────────────────────────────────────────────

    def download_file(
        self, path: str, rev: Optional[str] = None
    ) -> tuple[FileMetadata, bytes]:
        """
        Download a file's content by path (or rev).
        Returns (FileMetadata, file_bytes).
        """
        md, response = self._dbx.files_download(path, rev=rev)
        with contextlib.closing(response):
            data = response.content
        logger.debug("Downloaded %s (%d bytes)", md.path_display, len(data))
        return md, data
