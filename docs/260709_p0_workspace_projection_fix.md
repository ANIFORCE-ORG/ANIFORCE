# P0 Workspace 投影修复说明

**日期**：2026-07-09  
**优先级**：P0 - 立即修复  
**状态**：✅ 已完成

---

## 修复内容

### 1. 关联/解绑操作增加 HITL 审批

#### 问题描述

以下 4 个写操作工具未配置审批，用户无法预览关联关系：

- `add_material_to_campaign` - 将素材关联到广告计划
- `remove_material_from_campaign` - 从广告计划移除素材
- `add_material_to_project` - 将素材关联到项目
- `remove_material_from_project` - 从项目移除素材

**风险等级**：中等（不涉及资源删除，但影响业务关系）

#### 修复方案

**后端**：`aniforce-agent/app/agent/runtime.py`

```python
APPROVAL_REQUIRED_TOOL_NAMES = [
    # 项目管理
    "create_project",
    "update_project",
    "delete_project",
    # 广告计划管理
    "create_campaign",
    "update_campaign",
    "update_campaign_status",
    "delete_campaign",
    # 素材管理
    "create_material",
    "update_material",
    "delete_material",
    # 关联/解绑操作（P0 修复：增加审批）✅ 新增
    "add_material_to_campaign",
    "remove_material_from_campaign",
    "add_material_to_project",
    "remove_material_from_project",
]
```

**System Prompt 更新**：`aniforce-agent/app/agent/prompts.py`

- ✅ 安全边界规则中增加关联操作需要审批的说明
- ✅ Workspace 协同规则中说明审批类操作包括关联/解绑
- ✅ Dynamic instructions 中增加关联操作审批提示
- ✅ `request_workspace_projection` docstring 更新

#### 预期效果

**用户场景：将素材关联到广告计划**

```
用户："把这个素材关联到该计划"
```

**修复前**：
```
Agent 调用 add_material_to_campaign(campaign_id, material_id)
→ 直接执行，用户看不到关联的是哪个素材
→ ❌ 无法预览和确认
```

**修复后**：
```
Agent 调用 add_material_to_campaign(campaign_id, material_id)
→ runtime.requires_action 触发 HITL
→ 右侧 Workspace 展示审批草稿：
   - 广告计划：[计划名称]
   - 待关联素材：[素材名称、预览图]
   - 操作：关联
→ 用户点击"确认"或"拒绝"
→ ✅ 用户可以预览并确认关联关系
```

---

### 2. `list_available_images` 投影修复

#### 问题描述

`list_available_images` 返回 backend 本地文件列表，用于素材上传前的选择：

- ❌ 没有对应的 Workspace Surface
- ❌ 未进入投影注册表
- ❌ Agent 调用后无法投影到右侧供用户浏览

#### 修复方案

**前端注册表**：`frontend/packages/main-app/src/store/workspace.ts`

```typescript
export const workspaceResultProjectionRegistry = {
  // ... 其他工具
  
  // P0 修复：list_available_images 投影到素材列表 ✅ 新增
  list_available_images: {
    surface: 'material.list',
    mode: 'readonly',
    resultToPayload: transformLocalFilesToMaterialsPayload,
  },
}
```

**转换函数**：

```typescript
/**
 * 将 list_available_images 的本地文件列表转换为素材列表格式
 * backend 返回格式可能是: { files: [...], images: [...] } 或直接是数组
 */
function transformLocalFilesToMaterialsPayload(result: unknown): Record<string, unknown> {
  // 1. 解析 JSON-like 结果
  // 2. 提取文件列表（支持多种字段名：files、images、items、list、data）
  // 3. 转换为统一素材格式：
  //    - 字符串 → 解析文件名、扩展名、生成 ID
  //    - 对象 → 映射字段到素材格式
  // 4. 标记来源为 'local'，状态为 'local_available'
  // 5. 返回 { materials: [...] }
}
```

**System Prompt 更新**：

```
展示型查询映射：
  list_available_images -> material.list（本地文件以素材列表形式展示）
```

#### 预期效果

**用户场景：浏览本地可用图片**

```
用户："有哪些本地图片可以上传？"
```

**修复前**：
```
Agent 调用 list_available_images()
→ 返回文件列表
→ ❌ 无法投影到 Workspace
→ 聊天区文字列出文件名
→ 用户体验差
```

**修复后**：
```
Agent 调用 list_available_images()
→ 返回文件列表
Agent 调用 request_workspace_projection(surface="material.list")
→ 前端转换：本地文件 → 素材格式
→ ✅ 右侧 Workspace 展示为素材卡片（带缩略图、文件名、类型）
→ 用户可以直观浏览和选择
```

---

## 验证测试用例

### 用例 1：素材关联审批

**输入**：
```
"把 test-image.png 关联到 Campaign_123"
```

**预期行为**：
1. Agent 调用 `add_material_to_campaign(campaign_id="Campaign_123", material_id="material_xxx")`
2. Runtime 触发 HITL
3. 右侧 Workspace 显示审批草稿：
   - 广告计划：Campaign_123
   - 待关联素材：test-image.png
   - 预览图：[素材缩略图]
4. 用户点击"确认"
5. 关联执行成功
6. 聊天区显示："已成功将素材关联到广告计划"

**验证点**：
- ✅ 是否触发 HITL
- ✅ Workspace 是否显示审批草稿
- ✅ 素材信息是否完整展示
- ✅ 确认后是否正确执行

---

### 用例 2：本地文件浏览

**输入**：
```
"有哪些本地图片可以用？"
```

**预期行为**：
1. Agent 调用 `list_available_images()`
2. Backend 返回本地文件列表
3. Agent 调用 `request_workspace_projection(surface="material.list", reason="用户需要浏览本地可用图片")`
4. 前端 `transformLocalFilesToMaterialsPayload` 转换文件列表
5. 右侧 Workspace 展示素材卡片（本地文件以素材形式展示）
6. 聊天区概括："已在右侧展示 N 个本地图片，你可以选择上传"

**验证点**：
- ✅ 是否调用 `request_workspace_projection`
- ✅ Workspace 是否展示素材列表
- ✅ 素材卡片是否包含：名称、类型、缩略图
- ✅ 标记为"本地文件"

---

### 用例 3：素材解绑审批

**输入**：
```
"把这个素材从项目里移除"
```

**预期行为**：
1. Agent 识别上下文中的素材和项目
2. Agent 调用 `remove_material_from_project(material_id="xxx", project_id="xxx")`
3. Runtime 触发 HITL
4. 右侧 Workspace 显示审批草稿：
   - 项目：[项目名称]
   - 待移除素材：[素材名称]
   - 操作：解绑
5. 用户确认或拒绝

**验证点**：
- ✅ 是否触发 HITL
- ✅ 操作类型是否正确标记为"解绑"
- ✅ 拒绝后是否不执行

---

## 影响范围

### 后端

- ✅ `aniforce-agent/app/agent/runtime.py` - 审批工具列表
- ✅ `aniforce-agent/app/agent/prompts.py` - System Prompt 和 Dynamic Instructions

### 前端

- ✅ `frontend/packages/main-app/src/store/workspace.ts` - 投影注册表 + 转换函数

### 兼容性

- ✅ 向后兼容：已有工具行为不变
- ✅ 新增审批：用户体验更安全，不破坏现有流程
- ✅ 新增投影：增强功能，不影响已有投影

---

## 部署建议

### 1. 部署顺序

```
后端 (runtime.py + prompts.py) → 前端 (workspace.ts)
```

**原因**：后端先部署可以立即生效审批保护，前端稍后部署不影响功能。

### 2. 灰度验证

**第一阶段**：内部测试环境
- 验证关联操作触发审批
- 验证本地文件投影
- 验证审批草稿展示

**第二阶段**：生产环境
- 观察审批通过率
- 收集用户反馈
- 监控 Workspace 投影错误

### 3. 回滚方案

如果发现问题，回滚步骤：

```bash
# 后端回滚
git revert <commit-hash>

# 前端回滚
git revert <commit-hash>
```

**临时禁用审批**（紧急情况）：

```python
# runtime.py
APPROVAL_REQUIRED_TOOL_NAMES = [
    # 临时移除关联操作
    # "add_material_to_campaign",
    # "remove_material_from_campaign",
    # ...
]
```

---

## 后续优化建议

### P1 - 短期优化

1. **批量关联操作**
   ```python
   @mcp.tool()
   async def batch_add_materials_to_campaign(
       campaign_id: str, 
       material_ids: list[str]
   ):
       """批量关联素材，一次审批"""
   ```

2. **关联预览增强**
   - Workspace 审批草稿中显示更多上下文
   - 显示"已有 N 个素材，新增 M 个"

3. **本地文件上传流程优化**
   - `list_available_images` 投影后，用户点击素材卡片触发上传
   - 上传完成后自动创建素材记录

---

## 总结

### 已完成

- ✅ 关联/解绑操作增加 HITL 审批
- ✅ `list_available_images` 投影到素材列表
- ✅ System Prompt 更新
- ✅ 投影注册表更新
- ✅ 文件转换函数实现

### 解决的问题

1. **用户无法预览关联关系** → 现在通过 HITL 审批预览
2. **本地文件无法可视化浏览** → 现在投影为素材卡片
3. **关联操作缺乏确认** → 现在必须用户确认才执行

### 用户体验提升

- ✅ 关联操作更安全：防止误操作
- ✅ 本地文件浏览更直观：卡片形式展示
- ✅ 交互流程更统一：所有写操作都有审批
