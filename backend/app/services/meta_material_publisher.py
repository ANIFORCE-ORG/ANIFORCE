"""Publish and remove canonical materials in Meta ad accounts."""

from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass
from typing import Any

import httpx

from app.services.object_storage import AliyunOssStorageService


@dataclass(frozen=True)
class PublishedMetaAsset:
    asset_type: str
    external_asset_id: str
    image_hash: str | None
    name: str | None
    status: str | None
    remote_url: str | None


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
    ) -> PublishedMetaAsset:
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

    def _publish_sync(
        self,
        material: dict[str, Any],
        ad_account_id: str,
        asset_type: str,
    ) -> PublishedMetaAsset:
        from facebook_business.api import FacebookAdsApi
        from facebook_business.adobjects.adaccount import AdAccount

        FacebookAdsApi.init(
            app_id=self.app_id,
            app_secret=self.app_secret,
            access_token=self.access_token,
        )
        account_id = ad_account_id if ad_account_id.startswith("act_") else f"act_{ad_account_id}"
        account = AdAccount(account_id)
        name = material.get("name") or material.get("id")

        if asset_type == "image":
            from facebook_business.adobjects.adimage import AdImage

            data = self._download_bytes(material)
            response = account.create_ad_image(
                params={"bytes": base64.b64encode(data).decode("ascii")}
            )
            payload = self._image_payload(response)
            return PublishedMetaAsset(
                asset_type="image",
                external_asset_id=str(payload.get("id") or payload.get("hash")),
                image_hash=payload.get("hash"),
                name=payload.get("name") or name,
                status=payload.get("status"),
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
        return PublishedMetaAsset(
            asset_type="video",
            external_asset_id=str(external_id),
            image_hash=None,
            name=payload.get("title") or name,
            status="processing",
            remote_url=None,
        )

    def _delete_sync(self, ad_account_id: str, asset_type: str, external_asset_id: str) -> None:
        from facebook_business.api import FacebookAdsApi
        from facebook_business.adobjects.adaccount import AdAccount

        FacebookAdsApi.init(
            app_id=self.app_id,
            app_secret=self.app_secret,
            access_token=self.access_token,
        )
        account_id = ad_account_id if ad_account_id.startswith("act_") else f"act_{ad_account_id}"
        account = AdAccount(account_id)
        if asset_type == "image":
            account.delete_ad_images(params={"hash": external_asset_id})
        elif asset_type == "video":
            account.delete_ad_videos(params={"video_id": external_asset_id})
        else:
            raise ValueError("asset_type must be image or video")

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
