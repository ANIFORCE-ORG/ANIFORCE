# 团队与组织入口合并及协作说明

更新时间：2026-05-27

## 1. 结论

产品界面统一使用“团队”表达；接口和数据库继续使用主干已经定义的
`Organization` 模型与 `/organizations` API。团队不是新的数据库对象，
不新增 `teams` 表，也不新增一套团队接口。

主干设计依据：

- `backend/docs/database/database-upgrade-plan-organization-authorization.md`
- `backend/app/api/v1/organization.py`
- `frontend/packages/main-app/src/api/organization.ts`

## 2. 前端入口合并

设置页面原有两个重复入口：

- `组织与权限`
- `系统账号设置` 下的 `我的团队`

调整后仅保留 `账号与团队` 入口，页面集中承载：

- 登录账号信息与密码修改
- 团队创建、加入、离开与解散
- 团队成员查看、添加和移除
- 成员角色展示

兼容处理：

- 旧路由 `/organization-settings` 重定向至 `/account-config`。
- 左侧栏“当前组织”调整为“当前团队”，数据读取改用主干
  `organizationApi.getMyOrganizations()`。
- 移除旧的前端 `organizations.ts`、`useOrganizationContext.ts` 和独立组织页，
  防止继续依赖不符合主干的数据字段及角色定义。

## 3. 与主干一致的数据口径

前端只使用主干现有字段：

```text
organizations:
id, name, org_code, description, owner_id, status, member_count, role, created_at

organization_members:
id, user_id, user_name, user_email, role, joined_at
```

角色只按主干定义展示：

```text
admin | member
```

平台授权继续遵循主干定义：

```text
PlatformConnection owner_id
SubAccountBinding
PlatformConnectionAuthorization
resource_type: platform_connection | sub_account
permission_level: read | execute | read_execute
```

## 4. 后端协作缺口

以下能力是前端页面需要、但应由后端在主干模型基础上确认或补齐的事项。
在接口落实之前，前端不创建新的数据库结构：

| 能力 | 当前前端调用 | 需要后端确认 |
| --- | --- | --- |
| 当前团队切换 | 当前仅保存在浏览器 | 是否提供当前组织上下文接口，或由每个业务查询显式传入 `organization_id` |
| 成员角色更新 | 页面当前仅展示/移除 | 是否补充管理员修改 `admin/member` 角色的接口 |
| 账户授权管理 | 平台连接页面已有基础连接/子账号入口 | 落实 `platform_connection_authorizations` 的授权、撤销和可访问账号查询 API |
| 业务数据隔离 | 创建项目和广告计划依赖团队上下文 | 明确 `Project/Campaign/Material/Report` 如何绑定或校验 `organization_id` |

## 5. 开发约束

- 前端显示“团队”，请求和类型继续复用 `Organization`。
- 不在前端定义与主干冲突的 `owner/manager/operator` 角色体系。
- 不为 Demo 流程推导或提交后端表结构变化。
- 后续涉及账号授权、项目归属或数据隔离的接口需求，先追加到协作文档，
  再由后端基于主干模型实现。
