"""Object storage service for Aliyun OSS uploads."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4
from datetime import datetime
import mimetypes
import re

import oss2
from fastapi import UploadFile

from app.config.settings import get_settings


@dataclass
class UploadedObject:
    object_key: str
    url: str
    size: int
    content_type: str


class ObjectStorageError(RuntimeError):
    pass


class AliyunOssStorageService:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.OSS_ACCESS_KEY_ID or not settings.OSS_ACCESS_KEY_SECRET:
            raise ObjectStorageError("OSS credentials are not configured")
        if not settings.OSS_ENDPOINT or not settings.OSS_BUCKET:
            raise ObjectStorageError("OSS endpoint or bucket is not configured")
        self.bucket_name = settings.OSS_BUCKET
        self.endpoint = settings.OSS_ENDPOINT.rstrip("/")
        self.public_base_url = settings.OSS_PUBLIC_BASE_URL.rstrip("/") if settings.OSS_PUBLIC_BASE_URL else ""
        auth = oss2.Auth(settings.OSS_ACCESS_KEY_ID, settings.OSS_ACCESS_KEY_SECRET)
        self.bucket = oss2.Bucket(auth, self.endpoint, self.bucket_name)

    async def upload_material(self, file: UploadFile, user_id: str) -> UploadedObject:
        filename = file.filename or "upload"
        data = await file.read()
        return self.upload_bytes(
            data=data,
            filename=filename,
            content_type=file.content_type,
            user_id=user_id,
            prefix="materials",
        )

    def upload_bytes(
        self,
        data: bytes,
        filename: str,
        content_type: str | None,
        user_id: str,
        prefix: str = "materials",
    ) -> UploadedObject:
        suffix = Path(filename).suffix.lower()
        safe_name = _safe_filename(Path(filename).stem) or "material"
        resolved_content_type = content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        today = datetime.utcnow().strftime("%Y/%m/%d")
        object_key = f"{prefix}/{user_id}/{today}/{uuid4().hex}_{safe_name}{suffix}"

        headers = {"Content-Type": resolved_content_type}
        result = self.bucket.put_object(object_key, data, headers=headers)
        if result.status not in {200, 201}:
            raise ObjectStorageError(f"OSS upload failed with status {result.status}")
        return UploadedObject(
            object_key=object_key,
            url=self.object_url(object_key),
            size=len(data),
            content_type=resolved_content_type,
        )

    def object_url(self, object_key: str) -> str:
        if self.public_base_url:
            return f"{self.public_base_url}/{object_key}"
        # Aliyun OSS virtual-hosted style URL. This may be private; use signed_url for browser display.
        if self.endpoint.startswith("https://"):
            host = self.endpoint.removeprefix("https://")
            return f"https://{self.bucket_name}.{host}/{object_key}"
        if self.endpoint.startswith("http://"):
            host = self.endpoint.removeprefix("http://")
            return f"http://{self.bucket_name}.{host}/{object_key}"
        return f"https://{self.bucket_name}.{self.endpoint}/{object_key}"

    def signed_url(
        self,
        object_key: str,
        expires: int = 3600,
        process: str | None = None,
    ) -> str:
        params = {"x-oss-process": process} if process else None
        return self.bucket.sign_url("GET", object_key, expires, params=params, slash_safe=True)

    def object_key_from_url(self, url: str) -> str | None:
        prefixes = []
        if self.endpoint.startswith("https://"):
            prefixes.append(f"https://{self.bucket_name}.{self.endpoint.removeprefix('https://')}/")
        if self.endpoint.startswith("http://"):
            prefixes.append(f"http://{self.bucket_name}.{self.endpoint.removeprefix('http://')}/")
        if self.public_base_url:
            prefixes.append(f"{self.public_base_url}/")
        for prefix in prefixes:
            if url.startswith(prefix):
                return url[len(prefix):]
        return None


def _safe_filename(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip(".-_")
    return normalized[:80]
