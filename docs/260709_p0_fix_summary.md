# P0 修复总结

**日期**: 2026-07-09  
**Commit**: `faa43de`  
**分支**: `feat/agent-debug-260701`

---

## 🎯 修复内容

### 1. 关联操作增加审批（4个工具）

```python
# aniforce-agent/app/agent/runtime.py
APPROVAL_REQUIRED_TOOL_NAMES = [
    # ... 已有工具
    "add_material_to_campaign",         # ✅ 新增
    "remove_material_from_campaign",     # ✅ 新增
    "add_material_to_project",           # ✅ 新增
    "remove_material_from_project",      # ✅ 新增
]
```

**效果**：
- ❌ 修复前：Agent 直接关联，用户无法预览
- ✅ 修复后：触发 HITL，Workspace 显示审批草稿供确认

---

### 2. 修复 `list_available_images` 投影

```typescript
// frontend/packages/main-app/src/store/workspace.ts
workspaceResultProjectionRegistry['list_available_images'] = {
    surface: 'material.list',
    mode: 'readonly',
    resultToPayload: transformLocalFilesToMaterialsPayload,  // ✅ 新增转换函数
}
```

**效果**：
- ❌ 修复前：本地文件列表无法投影，聊天区文字列出
- ✅ 修复后：投影为素材卡片，右侧 Workspace 可视化展示

---

## 📝 System Prompt 更新

### 更新点

1. **安全边界规则**：增加"关联/解绑操作需要审批"说明
2. **Workspace 协同规则**：补充 `list_available_images -> material.list` 映射
3. **素材关联场景**：优化流程描述，先投影再关联
4. **Dynamic Instructions**：增加关联操作审批提示

---

## ✅ 验证方式

### 测试用例 1：素材关联审批

```
用户输入："把这个素材关联到该计划"
```

**验证点**：
1. Agent 调用 `add_material_to_campaign`
2. Runtime 触发 `requires_action`
3. Workspace 显示审批草稿（计划名 + 素材名 + 预览）
4. 用户点击"确认"后执行

---

### 测试用例 2：本地文件浏览

```
用户输入："有哪些本地图片可以上传？"
```

**验证点**：
1. Agent 调用 `list_available_images()`
2. Agent 调用 `request_workspace_projection(surface="material.list")`
3. Workspace 显示素材卡片（包含文件名、类型、缩略图）
4. 卡片标记为"本地文件"

---

## 📊 影响范围

| 模块 | 文件 | 改动类型 |
|------|------|---------|
| Agent Runtime | `aniforce-agent/app/agent/runtime.py` | 审批列表扩展 |
| Agent Prompt | `aniforce-agent/app/agent/prompts.py` | System Prompt 更新 |
| Workspace Store | `frontend/packages/main-app/src/store/workspace.ts` | 投影注册表 + 转换函数 |
| 文档 | `docs/260709_p0_workspace_projection_fix.md` | 详细说明文档 |

**总改动**：
- +487 行
- -117 行
- 4 个文件

---

## 🚀 部署建议

### 部署顺序
```
1. 后端（runtime.py + prompts.py）
2. 前端（workspace.ts）
```

### 验证步骤
1. 测试关联操作是否触发审批
2. 测试本地文件是否正确投影
3. 测试审批草稿展示是否完整

### 回滚方案
```bash
git revert faa43de
```

---

## 📈 用户体验提升

| 场景 | 修复前 | 修复后 |
|------|-------|-------|
| **素材关联** | ❌ 直接执行，无预览 | ✅ 审批草稿，可预览确认 |
| **本地文件浏览** | ❌ 文字列表，不直观 | ✅ 素材卡片，可视化展示 |
| **误操作风险** | ⚠️ 高（无确认） | ✅ 低（必须确认） |

---

## 🔗 相关文档

- [完整修复说明](./260709_p0_workspace_projection_fix.md)
- [Workspace 投影策略设计](./260708_01_workspace_projection_policy_design.md)
- [Agent 开发规范](../AGENTS.md)
