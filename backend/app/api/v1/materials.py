"""素材管理 API"""
import os
import base64
import json
import re
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.database import get_db
from app.repositories.protocols import MaterialRepository
from app.repositories.factory import get_material_repo
from app.api.deps import get_current_user
from app.config.settings import get_settings
from app.schemas.material import MaterialCreate

router = APIRouter(prefix="/materials", tags=["materials"])
settings = get_settings()

# 图像存储路径
IMAGES_DIR = Path(__file__).parent.parent.parent.parent / "data" / "images"
PUBLIC_CREATIVE_IMAGES_DIR = (
    Path(__file__).resolve().parents[4]
    / "frontend"
    / "packages"
    / "main-app"
    / "public"
    / "images"
    / "creatives"
)


def _resolve_image_path(image_url: str) -> Path | None:
    filename = os.path.basename(image_url)
    candidates = [
        IMAGES_DIR / filename,
        PUBLIC_CREATIVE_IMAGES_DIR / filename,
    ]
    return next((path for path in candidates if path.exists()), None)


def _safe_filename(filename: str) -> str:
    name = os.path.basename(filename)
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(name).stem).strip("._") or "material"
    suffix = Path(name).suffix.lower()
    return f"{stem}_{uuid.uuid4().hex[:8]}{suffix}"


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
        if not materials and settings.DEMO_MODE:
            materials = await material_repo.list_by_user(
                "user_test_001", type=type, limit=limit
            )
    
    return {"materials": materials}


@router.get("/images/list")
async def list_available_images(
    current_user: dict = Depends(get_current_user),
):
    """列出所有可用的图像文件"""
    images = []
    seen = set()
    for image_dir in [IMAGES_DIR, PUBLIC_CREATIVE_IMAGES_DIR]:
        if not image_dir.exists():
            continue
        for file_path in image_dir.iterdir():
            if (
                file_path.is_file()
                and file_path.suffix.lower() in [".jpg", ".jpeg", ".png", ".gif", ".webp"]
                and file_path.name not in seen
            ):
                seen.add(file_path.name)
                images.append({
                    "filename": file_path.name,
                    "size": file_path.stat().st_size,
                    "url": f"/images/creatives/{file_path.name}"
                })
    
    return {"images": images}


@router.post("")
async def create_material(
    request: MaterialCreate,
    current_user: dict = Depends(get_current_user),
    material_repo: MaterialRepository = Depends(get_material_repo),
    session: AsyncSession = Depends(get_db),
):
    """创建新素材"""
    material = await material_repo.create(
        user_id=current_user["id"],
        name=request.name or "未命名素材",
        type=request.type,
        url=request.url,
        thumbnail_url=request.thumbnail_url,
        project_ids=request.project_ids or [],
        campaign_ids=request.campaign_ids or [],
        tags=request.tags or [],
        ctr_estimate=request.ctr_estimate,
        media_type=request.media_type,
        fatigue=request.fatigue,
        is_hero=request.is_hero,
        duration=request.duration,
        file_size=request.file_size,
        roi=request.roi,
        spend=request.spend,
        campaign_id=request.campaign_id,
    )
    await session.commit()
    return material


@router.post("/upload")
async def upload_material(
    file: UploadFile = File(...),
    name: str | None = Form(None),
    type: str = Form("full_video"),
    tags: str | None = Form(None),
    project_ids: str | None = Form(None),
    current_user: dict = Depends(get_current_user),
    material_repo: MaterialRepository = Depends(get_material_repo),
    session: AsyncSession = Depends(get_db),
):
    """上传素材文件并创建素材记录"""
    allowed_content_types = {
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "video/mp4",
        "video/quicktime",
    }
    if file.content_type not in allowed_content_types:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    filename = _safe_filename(file.filename or "material")
    path = IMAGES_DIR / filename
    data = await file.read()
    if len(data) > 100 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large")
    try:
        path.write_bytes(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    def parse_json_list(value: str | None) -> list[str]:
        if not value:
            return []
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return [item.strip() for item in value.split(",") if item.strip()]

    media_type = "image" if (file.content_type or "").startswith("image/") else "video"
    url = f"/images/{filename}"
    material = await material_repo.create(
        user_id=current_user["id"],
        name=name or Path(file.filename or filename).stem,
        type=type,
        url=url,
        thumbnail_url=url,
        project_ids=parse_json_list(project_ids),
        campaign_ids=[],
        tags=parse_json_list(tags) or ["uploaded"],
        ctr_estimate=0,
        media_type=media_type,
        fatigue=0,
        is_hero=False,
        file_size=len(data),
    )
    await session.commit()
    return material


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
    
    image_url = material.get("thumbnail_url") if thumbnail else material.get("url")
    if not image_url:
        raise HTTPException(status_code=404, detail="Image not found")
    
    image_path = _resolve_image_path(image_url)
    if not image_path:
        raise HTTPException(status_code=404, detail="Image file not found")
    
    # 读取图像并转换为Base64
    try:
        with open(image_path, "rb") as f:
            image_data = f.read()
        
        # 获取文件扩展名以确定MIME类型
        ext = image_path.suffix.lower()
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        mime_type = mime_types.get(ext, "image/jpeg")
        
        # Base64编码
        base64_data = base64.b64encode(image_data).decode("utf-8")
        
        return {
            "material_id": material_id,
            "filename": image_path.name,
            "mime_type": mime_type,
            "size": len(image_data),
            "data": f"data:{mime_type};base64,{base64_data}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read image: {str(e)}")


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
