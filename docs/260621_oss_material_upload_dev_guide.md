# OSS 素材上传开发说明

日期：2026-06-21

## 目标

补齐 ANIFORCE 素材库的文件上传能力：用户在前端素材页选择图片/视频后，后端上传到阿里云 OSS，并在 `materials` 表创建素材记录，前端可通过签名 URL 正常展示图片素材。

当前实现是 MVP 版本，优先保证上传、入库、展示闭环可用。

## 当前架构

```text
Frontend Material.vue
  └─ uploadMaterials(files)
      └─ POST /api/v1/materials/upload multipart/form-data
          └─ Backend ObjectStorageService
              ├─ 上传文件到 Aliyun OSS
              └─ 创建 materials DB 记录

Frontend Material.vue
  └─ getMaterialImage(material_id, thumbnail=true)
      └─ GET /api/v1/materials/{material_id}/image
          └─ 后端为私有 OSS 对象签发短期 GET URL
```

## 配置

OSS 配置读取自 `backend/.env`：

```env
OSS_ACCESS_KEY_ID=...
OSS_ACCESS_KEY_SECRET=...
OSS_REGION=ap-southeast-1
OSS_ENDPOINT=https://oss-ap-southeast-1.aliyuncs.com
OSS_BUCKET=aniforce-creative
OSS_PUBLIC_BASE_URL=
```

说明：

- `OSS_BUCKET` 当前为 `aniforce-creative`。
- 当前 bucket 是私有读，不能直接用裸 OSS URL 在浏览器展示。
- 后端通过 `bucket.sign_url("GET", object_key, expires, slash_safe=True)` 生成短期签名 URL。
- `.env` 当前被项目 `.gitignore` 忽略，代码仓库不保存密钥。

## 后端实现

### 文件

- `backend/app/services/object_storage.py`
- `backend/app/api/v1/materials.py`
- `backend/app/config/settings.py`
- `backend/requirements.txt`

### 上传接口

```http
POST /api/v1/materials/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data

files=<file1>
files=<file2>
```

返回：

```json
{
  "materials": [
    {
      "id": "...",
      "user_id": "...",
      "name": "...",
      "type": "a_segment",
      "status": "ready",
      "url": "https://aniforce-creative.oss-ap-southeast-1.aliyuncs.com/materials/...",
      "thumbnail_url": "https://aniforce-creative.oss-ap-southeast-1.aliyuncs.com/materials/...",
      "file_size": 2785322,
      "tags": ["uploaded"],
      "project_ids": [],
      "campaign_ids": []
    }
  ]
}
```

### 文件校验

当前允许的 MIME：

```text
image/jpeg
image/png
image/gif
image/webp
video/mp4
video/quicktime
```

当前大小限制：`100MB`。

### OSS object key 规则

上传素材 key：

```text
materials/{user_id}/{YYYY}/{MM}/{DD}/{uuid}_{safe_filename}.{ext}
```

示例：

```text
materials/user_test_001/2026/06/21/d3fc4fac7e194828bb3d65e58db1f845_01-cover.png
```

### 素材类型映射

当前 MVP 映射：

```text
video/* -> full_video
image/* -> a_segment
```

后续如果需要更细分素材类型，可在上传表单或后端推断逻辑中扩展。

## 前端实现

### 文件

- `frontend/packages/main-app/src/api/materials.ts`
- `frontend/packages/main-app/src/pages/creatives/Material.vue`

### 上传流程

```text
用户选择或拖拽文件
  → 前端校验 MIME 和大小
  → uploadMaterials(files)
  → 后端上传 OSS 并创建 Material
  → 上传成功后 refreshMaterials()
  → 素材页重新请求列表和图片签名 URL
```

### 展示流程

素材页调用：

```ts
getMaterialImage(material.id, true)
```

后端如果识别到 `url` 是 OSS 对象，会返回：

```json
{
  "material_id": "mat_001",
  "filename": "creative_game_001.jpg",
  "mime_type": "image/jpeg",
  "size": 159532,
  "data": "",
  "url": "https://...签名URL..."
}
```

前端展示优先级：

```text
imageData.url || imageData.data || material.thumbnail_url || material.url
```

## 当前 DB 字段

`materials` 表当前仍复用历史字段：

```text
url
thumbnail_url
file_size
duration
```

当前 `url` / `thumbnail_url` 存储 OSS 裸 URL。由于 bucket 是私有读，裸 URL 只作为 object 定位源，不直接用于浏览器访问；浏览器展示使用后端签发的短期 URL。

## 已验证

### OSS 凭证和 bucket

- `list_buckets` 成功。
- bucket：`aniforce-creative`
- location：`oss-ap-southeast-1`
- endpoint：`https://oss-ap-southeast-1.aliyuncs.com`

### 上传闭环

已验证：

```text
POST /api/v1/materials/upload
  → OSS put_object 成功
  → materials DB 记录创建成功
  → GET /materials/{id} 返回正常
  → GET /materials/{id}/image 返回签名 URL
  → 签名 URL GET 成功，Content-Type 正确
```

示例上传素材：

```text
id: 65e6b157-207a-46c8-a375-81c6f8040486
name: 01-cover
file_size: 2785322
content-type: image/png
```

## 后续建议

MVP 当前可用，但生产级文件管理建议后续补充：

1. `materials` 表增加 `bucket`、`object_key`、`content_type`、`etag`、`storage_provider` 字段。
2. 删除素材时同步删除 OSS 对象，或进入异步回收队列。
3. 图片上传后生成标准缩略图，视频上传后抽帧生成封面。
4. 大文件上传改为前端预签名直传，后端只负责签名和 complete 确认。
5. 增加安全扫描、文件 hash 校验、重复上传检测。
6. 将通用文件能力抽象为 `files` 表，素材只引用 `file_id`。

## 常用校验命令

后端编译：

```bash
cd backend
source .venv/bin/activate
python -m py_compile app/api/v1/materials.py app/services/object_storage.py app/config/settings.py
```

前端构建：

```bash
cd frontend/packages/main-app
npm_config_cache=../../../npm_cache npm run build
```
