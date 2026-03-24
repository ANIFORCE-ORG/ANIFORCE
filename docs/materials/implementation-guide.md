# 图像同步功能实施指南

本文档说明如何使用已实施的图像数据前后端同步功能。

## 实施概览

已完成技术方案一（RESTful API + Base64编码）的第一阶段和第二阶段：

### ✅ 第一阶段：基础API开发
- 创建了 `/api/v1/materials` 路由
- 实现了图像数据CRUD操作
- 添加了Base64编码图像传输功能

### ✅ 第二阶段：前端集成
- 开发了materials API客户端
- 创建了图像展示组件
- 实现了图像查看器

## 文件结构

### 后端文件
```
backend/
├── app/
│   ├── api/v1/
│   │   ├── materials.py          # 素材管理API路由
│   │   └── router.py              # 已更新，包含materials路由
│   ├── repositories/
│   │   ├── impl/
│   │   │   └── sqlite_material_repo.py  # 素材数据访问层
│   │   └── factory.py             # Repository工厂
│   └── models/
│       └── material.py            # 素材数据模型
└── data/
    └── images/                    # 图像存储目录（23个图像文件）
```

### 前端文件
```
frontend/packages/main-app/src/
├── api/
│   └── materials.ts               # 素材API客户端
├── components/materials/
│   ├── MaterialImageGallery.vue   # 图像画廊组件
│   └── MaterialImageViewer.vue    # 图像查看器组件
├── pages/
│   └── Materials.vue              # 素材管理页面
└── router/
    └── index.ts                   # 已更新，包含/materials路由
```

## API接口说明

### 1. 获取素材列表
```
GET /api/v1/materials
Query参数:
  - project_id: 项目ID（可选）
  - campaign_id: 广告计划ID（可选）
  - type: 素材类型（可选）
  - limit: 返回数量限制（默认50）
```

### 2. 获取素材详情
```
GET /api/v1/materials/{material_id}
```

### 3. 获取素材图像（Base64编码）
```
GET /api/v1/materials/{material_id}/image
Query参数:
  - thumbnail: 是否获取缩略图（默认false）

返回格式:
{
  "material_id": "string",
  "filename": "string",
  "mime_type": "image/jpeg",
  "size": 12345,
  "data": "data:image/jpeg;base64,..."
}
```

### 4. 列出所有可用图像
```
GET /api/v1/materials/images/list
```

### 5. 创建素材
```
POST /api/v1/materials
Body:
{
  "name": "素材名称",
  "type": "a_segment",
  "url": "/images/filename.jpg",
  "thumbnail_url": "/images/filename.jpg",
  "project_ids": [],
  "campaign_ids": [],
  "tags": [],
  "ctr_estimate": 0.05
}
```

## 前端使用示例

### 1. 获取素材列表
```typescript
import { getMaterials } from '@/api/materials'

const materials = await getMaterials({
  project_id: 'proj_001',
  limit: 20
})
```

### 2. 获取图像数据
```typescript
import { getMaterialImage } from '@/api/materials'

const image = await getMaterialImage('material_id', false)
// image.data 包含完整的 data URL，可直接用于 <img src="">
```

### 3. 使用图像画廊组件
```vue
<template>
  <MaterialImageGallery
    :project-id="projectId"
    @select-material="handleSelectMaterial"
    @select-image="handleSelectImage"
  />
</template>

<script setup>
import MaterialImageGallery from '@/components/materials/MaterialImageGallery.vue'

const handleSelectMaterial = (material) => {
  console.log('选中素材:', material)
}

const handleSelectImage = (image) => {
  console.log('图像数据:', image.data)
}
</script>
```

### 4. 使用图像查看器
```vue
<template>
  <MaterialImageViewer
    :image="selectedImage"
    :show="showViewer"
    @close="showViewer = false"
  />
</template>

<script setup>
import { ref } from 'vue'
import MaterialImageViewer from '@/components/materials/MaterialImageViewer.vue'

const selectedImage = ref(null)
const showViewer = ref(false)
</script>
```

## 访问素材管理页面

启动应用后，访问 `/materials` 路由即可查看素材管理页面：
```
http://localhost:3010/materials
```

## 图像存储说明

- **存储位置**: `backend/data/images/`
- **支持格式**: JPG, JPEG, PNG, GIF, WebP
- **当前图像**: 23个素材图像文件已从前端迁移到后端

## 性能优化建议

### 已实现
- ✅ Base64编码传输
- ✅ 懒加载图像
- ✅ 缩略图支持
- ✅ 图像缓存（前端Map缓存）

### 待优化（第三阶段）
- ⏳ 图像压缩
- ⏳ 预加载策略
- ⏳ 浏览器缓存控制
- ⏳ 图像格式优化（WebP优先）

## 下一步计划

### 第三阶段：性能优化
1. 实现图像懒加载优化
2. 添加预加载策略
3. 优化用户体验
4. 添加加载进度指示

### 第四阶段：高级功能
1. 实现实时同步（WebSocket）
2. 添加图像编辑功能
3. 集成CDN服务
4. 批量上传和管理

## 故障排查

### 图像无法加载
1. 检查图像文件是否存在于 `backend/data/images/` 目录
2. 检查素材记录的url字段是否正确
3. 检查API认证token是否有效

### API请求失败
1. 确认后端服务已启动
2. 检查CORS配置
3. 查看浏览器控制台错误信息

### 组件不显示
1. 确认路由配置正确
2. 检查组件导入路径
3. 验证用户认证状态

## 技术支持

如有问题，请参考：
- 技术方案文档: `docs/materials/image-sync-solution.md`
- API文档: 启动后访问 `/docs`
- 代码示例: `frontend/packages/main-app/src/pages/Materials.vue`
