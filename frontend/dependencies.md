# 前端依赖清单

> 前端使用 `pnpm` 管理依赖，依赖声明在各 `package.json` 中。
> 安装命令：`pnpm install`（在 `frontend/` 目录下执行即可安装所有子包依赖）

## main-app（Vue3 主应用）

### 运行时依赖

| 包名 | 版本 | 用途 |
|------|------|------|
| vue | ^3.4.21 | UI 框架 |
| vue-router | ^4.3.0 | 路由管理 |
| pinia | ^2.1.7 | 状态管理 |
| axios | ^1.7.2 | HTTP 客户端 |
| @animagus/shared | workspace:* | 共享类型、DAL、常量 |

### 开发依赖

| 包名 | 版本 | 用途 |
|------|------|------|
| vite | ^5.2.11 | 构建工具 |
| @vitejs/plugin-vue | ^5.0.4 | Vite Vue3 插件 |
| typescript | ^5.4.5 | 类型检查 |
| vue-tsc | ^2.0.16 | Vue TypeScript 编译 |
| tailwindcss | ^3.4.3 | 原子化 CSS |
| postcss | ^8.4.38 | CSS 后处理 |
| autoprefixer | ^10.4.19 | 浏览器前缀自动补全 |

## shared（共享包）

纯 TypeScript 包，无额外运行时依赖。提供：
- **types/** — 统一类型定义（ApiResponse、Trend、Material 等）
- **dal/** — 数据访问层接口、MockClient、HttpClient、工厂
- **utils/** — 常量定义
