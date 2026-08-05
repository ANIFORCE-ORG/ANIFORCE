from __future__ import annotations

from facebook_business.adobjects.adaccount import AdAccount

from app.services.meta_material_publisher import MetaMaterialPublisher, _video_error_message


class FakeImageResponse:
    def export_all_data(self) -> dict:
        return {"hash": "image-hash-1", "name": "Uploaded image"}


def test_image_upload_without_status_requires_remote_verification(monkeypatch) -> None:
    publisher = MetaMaterialPublisher("token", "app-id", "app-secret")
    monkeypatch.setattr(publisher, "_api", lambda: None)
    monkeypatch.setattr(publisher, "_download_bytes", lambda _: b"image-bytes")
    monkeypatch.setattr(
        AdAccount,
        "create_ad_image",
        lambda self, params: FakeImageResponse(),
    )

    result = publisher._publish_sync(
        {"id": "material-1", "name": "Image", "url": "https://example.com/image.jpg"},
        "act_123",
        "image",
    )

    assert result.external_asset_id == "image-hash-1"
    assert result.image_hash == "image-hash-1"
    assert result.remote_status == "processing"


def test_image_payload_supports_raw_meta_images_response() -> None:
    payload = MetaMaterialPublisher._image_payload(
        {
            "images": {
                "upload.jpg": {
                    "hash": "image-hash-2",
                    "url": "https://meta.example/image.jpg",
                }
            }
        }
    )

    assert payload["hash"] == "image-hash-2"


def test_video_processing_error_extracts_official_status_message() -> None:
    message = _video_error_message(
        {
            "video_status": "error",
            "processing_phase": {
                "status": "error",
                "errors": [{"code": 6000, "message": "Video format is unsupported"}],
            },
        }
    )

    assert message == "Video format is unsupported"
