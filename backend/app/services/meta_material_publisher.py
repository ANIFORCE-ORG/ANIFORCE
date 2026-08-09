"""Publish and remove canonical materials in Meta ad accounts."""

from __future__ import annotations

import asyncio
import base64
from typing import Any

import httpx

from app.services.material_platform_provider import (
    PlatformAssetNotFound,
    PlatformAssetState,
    PublishedPlatformAsset,
    normalize_platform_status,
)
from app.services.object_storage import AliyunOssStorageService


class MetaMaterialPublisher:
    """Use Meta AdImage/AdVideo APIs without creating creatives or ads."""

    def __init__(self, access_token: str, app_id: str, app_secret: str) -> None:
        self.access_token = access_token
        self.app_id = app_id
        self.app_secret = app_secret
        self.storage = AliyunOssStorageService()

    async def publish(
        self,
        *,
        material: dict[str, Any],
        ad_account_id: str,
        asset_type: str,
    ) -> PublishedPlatformAsset:
        if asset_type not in {"image", "video"}:
            raise ValueError("asset_type must be image or video")
        if not material.get("url"):
            raise ValueError("Material has no source file")
        return await asyncio.to_thread(
            self._publish_sync,
            material,
            ad_account_id,
            asset_type,
        )

    async def delete(
        self,
        *,
        ad_account_id: str,
        asset_type: str,
        external_asset_id: str,
    ) -> None:
        await asyncio.to_thread(
            self._delete_sync,
            ad_account_id,
            asset_type,
            external_asset_id,
        )

    async def get_state(
        self,
        *,
        ad_account_id: str,
        asset_type: str,
        external_asset_id: str,
    ) -> PlatformAssetState:
        return await asyncio.to_thread(
            self._get_state_sync,
            ad_account_id,
            asset_type,
            external_asset_id,
        )

    def _publish_sync(
        self,
        material: dict[str, Any],
        ad_account_id: str,
        asset_type: str,
    ) -> PublishedPlatformAsset:
        from facebook_business.adobjects.adaccount import AdAccount

        account_id = ad_account_id if ad_account_id.startswith("act_") else f"act_{ad_account_id}"
        account = AdAccount(account_id, api=self._api())
        name = material.get("name") or material.get("id")

        if asset_type == "image":
            from facebook_business.adobjects.adimage import AdImage

            data = self._download_bytes(material)
            response = account.create_ad_image(
                params={"bytes": base64.b64encode(data).decode("ascii")}
            )
            payload = self._image_payload(response)
            external_id = payload.get("id") or payload.get("hash")
            if not external_id:
                raise RuntimeError("Meta image upload returned no image identity")
            return PublishedPlatformAsset(
                asset_type="image",
                external_asset_id=str(external_id),
                image_hash=payload.get("hash"),
                name=payload.get("name") or name,
                # A returned hash confirms acceptance; readiness is verified by GET /adimages.
                remote_status=payload.get("status") or "processing",
                remote_url=payload.get("url"),
            )

        from facebook_business.adobjects.advideo import AdVideo

        source_url = self._signed_source_url(material)
        response = account.create_ad_video(
            params={
                "file_url": source_url,
                "title": name,
                "description": material.get("creator") or "",
            }
        )
        payload = response.export_all_data() if hasattr(response, "export_all_data") else dict(response)
        external_id = payload.get("id") or payload.get("video_id")
        if not external_id:
            raise RuntimeError("Meta video upload returned no video ID")
        return PublishedPlatformAsset(
            asset_type="video",
            external_asset_id=str(external_id),
            image_hash=None,
            name=payload.get("title") or name,
            remote_status="processing",
            remote_url=None,
        )

    def _delete_sync(self, ad_account_id: str, asset_type: str, external_asset_id: str) -> None:
        from facebook_business.adobjects.adaccount import AdAccount

        account_id = ad_account_id if ad_account_id.startswith("act_") else f"act_{ad_account_id}"
        account = AdAccount(account_id, api=self._api())
        if asset_type == "image":
            account.delete_ad_images(params={"hash": external_asset_id})
        elif asset_type == "video":
            account.delete_ad_videos(params={"video_id": external_asset_id})
        else:
            raise ValueError("asset_type must be image or video")

    def _get_state_sync(
        self, ad_account_id: str, asset_type: str, external_asset_id: str
    ) -> PlatformAssetState:
        if asset_type == "image":
            from facebook_business.adobjects.adaccount import AdAccount

            account_id = ad_account_id if ad_account_id.startswith("act_") else f"act_{ad_account_id}"
            rows = AdAccount(account_id, api=self._api()).get_ad_images(
                fields=["hash", "status", "url", "url_128"],
                params={"hashes": [external_asset_id]},
            )
            image = next(iter(rows), None)
            if image is None:
                raise PlatformAssetNotFound("Platform image asset no longer exists")
            payload = image.export_all_data() if hasattr(image, "export_all_data") else dict(image)
            remote_status = payload.get("status") or "ready"
            return PlatformAssetState(
                remote_status=remote_status,
                normalized_status=normalize_platform_status(remote_status),
                remote_url=payload.get("url"),
                remote_thumbnail_url=payload.get("url_128"),
            )
        if asset_type != "video":
            raise ValueError("asset_type must be image or video")

        from facebook_business.adobjects.advideo import AdVideo

        video = AdVideo(external_asset_id, api=self._api())
        try:
            payload = video.api_get(fields=["status", "source", "picture"]).export_all_data()
        except Exception as exc:
            if _is_not_found(exc):
                raise PlatformAssetNotFound("Platform video asset no longer exists") from exc
            raise
        status_payload = payload.get("status")
        error_message = _video_error_message(status_payload)
        status_value = status_payload
        if isinstance(status_value, dict):
            status_value = status_value.get("video_status") or status_value.get("status")
        remote_status = str(status_value) if status_value is not None else None
        return PlatformAssetState(
            remote_status=remote_status,
            normalized_status=normalize_platform_status(remote_status),
            remote_url=payload.get("source"),
            remote_thumbnail_url=payload.get("picture"),
            error_message=error_message,
        )

    def _api(self):
        from facebook_business.api import FacebookAdsApi
        from facebook_business.session import FacebookSession

        return FacebookAdsApi(
            FacebookSession(self.app_id, self.app_secret, self.access_token)
        )

    def _signed_source_url(self, material: dict[str, Any]) -> str:
        object_key = material.get("storage_object_key")
        if object_key:
            return self.storage.signed_url(object_key, expires=3600)
        return str(material["url"])

    def _download_bytes(self, material: dict[str, Any]) -> bytes:
        object_key = material.get("storage_object_key")
        if object_key:
            return self.storage.bucket.get_object(object_key).read()
        with httpx.Client(follow_redirects=True, timeout=90.0) as client:
            response = client.get(str(material["url"]))
            response.raise_for_status()
            return response.content

    @staticmethod
    def _image_payload(response: Any) -> dict[str, Any]:
        if hasattr(response, "export_all_data"):
            data = response.export_all_data()
        elif isinstance(response, dict):
            data = response
        else:
            data = dict(response)
        images = data.get("images")
        if isinstance(images, dict) and images:
            return next(iter(images.values()))
        if isinstance(images, list) and images:
            return images[0]
        return data


def _video_error_message(status: Any) -> str | None:
    if not isinstance(status, dict):
        return None
    processing_phase = status.get("processing_phase")
    errors = (
        processing_phase.get("errors")
        if isinstance(processing_phase, dict)
        else None
    ) or status.get("errors")
    if not errors:
        return None
    if not isinstance(errors, list):
        errors = [errors]
    messages = []
    for error in errors:
        if isinstance(error, dict):
            message = error.get("message") or error.get("error_message") or error.get("description")
            if message:
                messages.append(str(message))
        elif error:
            messages.append(str(error))
    return "; ".join(messages) or "Meta video processing failed"


def _is_not_found(error: Exception) -> bool:
    http_status = getattr(error, "http_status", None)
    api_code = getattr(error, "api_error_code", None)
    status = http_status() if callable(http_status) else None
    code = api_code() if callable(api_code) else None
    return status == 404 or code in {100}
