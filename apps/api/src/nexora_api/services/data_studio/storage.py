"""Constrained filesystem storage for imported and canonical dataset files."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from nexora_api.core.exceptions import DataStudioError
from nexora_api.services.data_studio.constants import ALLOWED_EXTENSIONS, ALLOWED_MIME_TYPES


@dataclass(frozen=True)
class StoredFile:
    original_filename: str
    relative_path: str
    file_type: str
    mime_type: str
    size: int
    sha256: str


class StorageService:
    """Own all writes beneath one configured data directory."""

    def __init__(self, root: Path, max_upload_bytes: int) -> None:
        self.root = root.resolve()
        self.max_upload_bytes = max_upload_bytes
        self.uploads = self.root / "uploads"
        self.processed = self.root / "processed"
        self.demo = self.root / "demo"
        for directory in (self.root, self.uploads, self.processed, self.demo):
            directory.mkdir(parents=True, exist_ok=True)

    def resolve_owned_path(self, relative_path: str) -> Path:
        """Resolve a persisted relative path and reject attempts to leave storage."""
        candidate = (self.root / relative_path).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise DataStudioError("unsafe_path", "The stored dataset path is invalid.", 500)
        return candidate

    @staticmethod
    def _validate_metadata(filename: str | None, content_type: str | None) -> tuple[str, str]:
        if not filename or not filename.strip():
            raise DataStudioError("missing_filename", "Choose a CSV or Excel file to continue.")
        display_name = Path(filename.replace("\x00", "")).name[:255]
        extension = Path(display_name).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise DataStudioError(
                "unsupported_format", "Only CSV, XLSX, and XLS files are supported."
            )
        normalized_mime = (content_type or "").lower().split(";", maxsplit=1)[0]
        if normalized_mime not in ALLOWED_MIME_TYPES:
            raise DataStudioError(
                "invalid_content_type", "The file type does not match a supported tabular format."
            )
        return display_name, extension

    async def save_upload(self, upload: UploadFile, dataset_id: str) -> StoredFile:
        """Stream an upload to a UUID-named file while hashing and enforcing size."""
        display_name, extension = self._validate_metadata(upload.filename, upload.content_type)
        relative_path = f"uploads/{dataset_id}{extension}"
        destination = self.resolve_owned_path(relative_path)
        digest = hashlib.sha256()
        size = 0
        try:
            with destination.open("xb") as target:
                while chunk := await upload.read(1024 * 1024):
                    size += len(chunk)
                    if size > self.max_upload_bytes:
                        raise DataStudioError(
                            "file_too_large",
                            "The local upload limit is "
                            f"{self.max_upload_bytes // (1024 * 1024)} MB.",
                            413,
                        )
                    digest.update(chunk)
                    target.write(chunk)
        except FileExistsError as exc:
            raise DataStudioError(
                "storage_conflict", "Could not allocate dataset storage.", 409
            ) from exc
        except Exception:
            if destination.exists():
                destination.unlink()
            raise
        finally:
            await upload.close()

        if size == 0:
            destination.unlink(missing_ok=True)
            raise DataStudioError("empty_file", "The selected file is empty.")

        return StoredFile(
            original_filename=display_name,
            relative_path=relative_path,
            file_type=ALLOWED_EXTENSIONS[extension],
            mime_type=(upload.content_type or "application/octet-stream")[:120],
            size=size,
            sha256=digest.hexdigest(),
        )

    def save_demo_bytes(self, content: bytes, dataset_id: str) -> StoredFile:
        relative_path = f"demo/{dataset_id}.csv"
        destination = self.resolve_owned_path(relative_path)
        destination.write_bytes(content)
        return StoredFile(
            original_filename="nexora_synthetic_demand_demo.csv",
            relative_path=relative_path,
            file_type="csv",
            mime_type="text/csv",
            size=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
        )

    def write_processed_csv(self, content: str, dataset_id: str) -> str:
        relative_path = f"processed/{dataset_id}.csv"
        destination = self.resolve_owned_path(relative_path)
        destination.write_text(content, encoding="utf-8", newline="")
        return relative_path

    def remove_owned_file(self, relative_path: str | None) -> None:
        if relative_path:
            self.resolve_owned_path(relative_path).unlink(missing_ok=True)
