"""素材管理 API"""
import os
import base64
from pathlib import Path
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from app.repositories.protocols import MaterialRepository
from app.repositories.factory import get_material_repo
from app.api.deps import get_current_user
from app.config.settings import get_settings
from app.services.object_storage import AliyunOssStorageService, ObjectStorageError

router = APIRouter(prefix="/materials", tags=["materials"])
settings = get_settings()

# 图像存储路径
IMAGES_DIR = Path(__file__).parent.parent.parent.parent / "data" / "images"
FRONTEND_CREATIVE_IMAGES_DIR = (
    Path(__file__).resolve().parents[4]
    / "frontend"
    / "packages"
    / "main-app"
    / "public"
    / "images"
    / "creatives"
)


@router.get("")
async def list_materials(
    project_id: str | None = None,
    campaign_id: str | None = None,
    type: str | None = None,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
    material_repo: MaterialRepository = Depends(get_material_repo),
):
    """获取素材列表"""
    if project_id:
        materials = await material_repo.list_by_project(project_id, limit=limit)
    elif campaign_id:
        materials = await material_repo.list_by_campaign(campaign_id, limit=limit)
    else:
        materials = await material_repo.list_by_user(
            current_user["id"], type=type, limit=limit
        )
    
    return {"materials": materials}


@router.get("/{material_id}")
async def get_material(
    material_id: str,
    current_user: dict = Depends(get_current_user),
    material_repo: MaterialRepository = Depends(get_material_repo),
):
    """获取素材详情"""
    material = await material_repo.get_by_id(material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    # 验证权限
    if material["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    return material


@router.get("/{material_id}/image")
async def get_material_image(
    material_id: str,
    thumbnail: bool = False,
    current_user: dict = Depends(get_current_user),
    material_repo: MaterialRepository = Depends(get_material_repo),
):
    """获取素材图像（Base64编码）"""
    material = await material_repo.get_by_id(material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    # 验证权限
    if material["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # 获取素材路径：缩略图不存在时回退原始素材，兼容视频 MVP 预览。
    image_url = material.get("thumbnail_url") if thumbnail else material.get("url")
    if not image_url:
        image_url = material.get("url")
    if not image_url:
        raise HTTPException(status_code=404, detail="Material file not found")
    
    storage = _try_create_storage()
    if storage:
        object_key = storage.object_key_from_url(image_url)
        if object_key:
            filename = os.path.basename(object_key)
            return {
                "material_id": material_id,
                "filename": filename,
                "mime_type": _mime_type_from_filename(filename),
                "size": material.get("file_size") or 0,
                "data": "",
                "url": storage.signed_url(object_key),
            }

    # 从URL中提取文件名
    filename = os.path.basename(image_url)
    image_path = _resolve_local_image_path(image_url)
    
    if not image_path:
        raise HTTPException(status_code=404, detail="Image file not found")
    
    # 读取图像并转换为Base64
    try:
        with open(image_path, "rb") as f:
            image_data = f.read()
        
        # 获取文件扩展名以确定MIME类型
        ext = image_path.suffix.lower()
        mime_type = _mime_type_from_filename(image_path.name)
        
        # Base64编码
        base64_data = base64.b64encode(image_data).decode("utf-8")
        
        return {
            "material_id": material_id,
            "filename": filename,
            "mime_type": mime_type,
            "size": len(image_data),
            "data": f"data:{mime_type};base64,{base64_data}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read image: {str(e)}")


@router.get("/images/list")
async def list_available_images(
    current_user: dict = Depends(get_current_user),
):
    """列出所有可用的图像文件"""
    if not IMAGES_DIR.exists():
        return {"images": []}
    
    images = []
    for file_path in IMAGES_DIR.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
            images.append({
                "filename": file_path.name,
                "size": file_path.stat().st_size,
                "url": f"/images/{file_path.name}"
            })
    
    return {"images": images}


@router.post("/upload")
async def upload_materials(
    files: Annotated[list[UploadFile], File(description="素材文件，支持图片和视频")],
    current_user: dict = Depends(get_current_user),
    material_repo: MaterialRepository = Depends(get_material_repo),
):
    """上传素材文件到 OSS，并创建素材记录。"""
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    storage = AliyunOssStorageService()
    materials = []
    for file in files:
        _validate_upload_file(file)
        try:
            uploaded = await storage.upload_material(file, current_user["id"])
        except ObjectStorageError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Upload failed: {exc}") from exc

        material = await material_repo.create(
            user_id=current_user["id"],
            name=Path(file.filename or uploaded.object_key).stem,
            type=_material_type_from_content_type(uploaded.content_type),
            url=uploaded.url,
            thumbnail_url=uploaded.url if uploaded.content_type.startswith("image/") else None,
            project_ids=[],
            campaign_ids=[],
            tags=["uploaded"],
            file_size=uploaded.size,
        )
        materials.append(material)

    return {"materials": materials}


@router.post("")
async def create_material(
    name: str,
    type: str,
    url: str,
    thumbnail_url: str | None = None,
    project_ids: list[str] | None = None,
    campaign_ids: list[str] | None = None,
    tags: list[str] | None = None,
    ctr_estimate: float | None = None,
    current_user: dict = Depends(get_current_user),
    material_repo: MaterialRepository = Depends(get_material_repo),
):
    """创建新素材"""
    material = await material_repo.create(
        user_id=current_user["id"],
        name=name,
        type=type,
        url=url,
        thumbnail_url=thumbnail_url,
        project_ids=project_ids or [],
        campaign_ids=campaign_ids or [],
        tags=tags or [],
        ctr_estimate=ctr_estimate,
    )
    return material


@router.post("/{material_id}/projects/{project_id}")
async def add_material_to_project(
    material_id: str,
    project_id: str,
    current_user: dict = Depends(get_current_user),
    material_repo: MaterialRepository = Depends(get_material_repo),
):
    """添加素材到项目"""
    material = await material_repo.get_by_id(material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    if material["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    await material_repo.add_to_project(material_id, project_id)
    return {"message": "Material added to project successfully"}


@router.delete("/{material_id}/projects/{project_id}")
async def remove_material_from_project(
    material_id: str,
    project_id: str,
    current_user: dict = Depends(get_current_user),
    material_repo: MaterialRepository = Depends(get_material_repo),
):
    """从项目移除素材"""
    material = await material_repo.get_by_id(material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    if material["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    await material_repo.remove_from_project(material_id, project_id)
    return {"message": "Material removed from project successfully"}


def _validate_upload_file(file: UploadFile) -> None:
    allowed_types = {
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "video/mp4",
        "video/quicktime",
    }
    max_size = 100 * 1024 * 1024
    content_type = file.content_type or ""
    if content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {content_type or 'unknown'}")
    size = getattr(file, "size", None)
    if size is not None and size > max_size:
        raise HTTPException(status_code=400, detail="File exceeds 100MB limit")


def _material_type_from_content_type(content_type: str) -> str:
    if content_type.startswith("video/"):
        return "full_video"
    return "a_segment"


def _mime_type_from_filename(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    mime_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
    }
    return mime_types.get(ext, "application/octet-stream")


def _try_create_storage() -> AliyunOssStorageService | None:
    try:
        return AliyunOssStorageService()
    except ObjectStorageError:
        return None


def _resolve_local_image_path(image_url: str) -> Path | None:
    filename = os.path.basename(image_url)
    candidates = []
    if image_url.startswith("/images/creatives/"):
        candidates.append(FRONTEND_CREATIVE_IMAGES_DIR / filename)
    candidates.extend([
        IMAGES_DIR / filename,
        FRONTEND_CREATIVE_IMAGES_DIR / filename,
    ])
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


@router.delete("/{material_id}")
async def delete_material(
    material_id: str,
    current_user: dict = Depends(get_current_user),
    material_repo: MaterialRepository = Depends(get_material_repo),
):
    """删除素材"""
    material = await material_repo.get_by_id(material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    if material["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    await material_repo.delete(material_id)
    return {"message": "Material deleted successfully"}
