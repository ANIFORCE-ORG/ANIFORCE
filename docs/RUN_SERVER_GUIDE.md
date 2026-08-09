# ANIMAGUS 启动脚本使用指南

## 📋 概述

`run_server.sh` 是 ANIMAGUS 项目的一键启动脚本，支持本地开发和云端部署两种模式。

## 🚀 基本用法

```bash
./run_server.sh [选项]
```

## 📝 参数说明

### 核心参数

| 参数 | 说明 | 默认值 | 示例 |
|------|------|--------|------|
| `--mode` | 启动模式：`local` 或 `cloud` | `local` | `--mode cloud` |
| `--demo` | 启用 Demo 模式 | `false`（生产模式） | `--demo` |
| `--only` | 仅启动指定服务：`all`、`backend`、`frontend` | `all` | `--only backend` |
| `--skip-install` | 跳过依赖安装 | 否 | `--skip-install` |
| `--daemon` | 后台常驻运行，退出终端后服务继续运行 | 否 | `--daemon` |

### 网络参数

| 参数 | 说明 | 默认值 | 示例 |
|------|------|--------|------|
| `--host` | 监听地址 | `0.0.0.0` | `--host 127.0.0.1` |
| `--frontend-port` | 前端端口 | `3010` | `--frontend-port 8080` |
| `--backend-port` | 后端端口 | `8010` | `--backend-port 9000` |

## 🎯 使用场景

### 1. 本地开发（生产模式）

**默认启动**：
```bash
./run_server.sh
```

**特点**：
- ✅ 使用真实数据库
- ✅ 用户注册写入数据库
- ✅ 支持热重载
- ✅ 自动打开浏览器
- ✅ 仅本地访问

### 2. 本地开发（Demo 模式）

**启动命令**：
```bash
./run_server.sh --demo
```

**特点**：
- ✅ 使用模拟数据
- ✅ 不写入真实数据库
- ✅ 快速原型验证
- ✅ 支持热重载
- ✅ 自动打开浏览器

### 3. 云端部署（生产模式）

**启动命令**：
```bash
./run_server.sh --mode cloud
```

**特点**：
- ✅ 多进程运行（2个工作进程）
- ✅ 允许外部访问
- ✅ 关闭热重载（性能优化）
- ✅ 使用真实数据库
- ❌ 不自动打开浏览器

### 4. 云端部署（Demo 模式）

**启动命令**：
```bash
./run_server.sh --mode cloud --demo
```

**特点**：
- ✅ 多进程运行
- ✅ 允许外部访问
- ✅ 使用模拟数据
- ✅ 适合演示环境

## 🔧 高级用法

### 后台常驻运行

```bash
./run_server.sh --mode local --daemon
```

启动过程写入 `logs/YYYYMMDD.local.launcher.log`。可使用 `./check_server.sh` 查看状态，使用 `./stop_server.sh` 停止服务。

### 仅启动后端

```bash
./run_server.sh --only backend
```

### 仅启动前端

```bash
./run_server.sh --only frontend
```

### 自定义端口

```bash
./run_server.sh --frontend-port 8080 --backend-port 9000
```

### 跳过依赖安装（加速启动）

```bash
./run_server.sh --skip-install
```

### 云端部署 + 自定义端口

```bash
./run_server.sh --mode cloud --frontend-port 80 --backend-port 8000
```

## 📊 模式对比

### Local vs Cloud 模式

| 特性 | Local 模式 | Cloud 模式 |
|------|-----------|-----------|
| **热重载** | ✅ 开启 | ❌ 关闭 |
| **工作进程** | 1个 | 2个 |
| **网络访问** | 仅本地 (127.0.0.1) | 所有网卡 (0.0.0.0) |
| **自动打开浏览器** | ✅ 是 | ❌ 否 |
| **适用场景** | 本地开发调试 | 云服务器部署 |
| **性能** | 开发模式 | 生产模式 |

### Demo vs 生产模式

| 特性 | Demo 模式 | 生产模式 |
|------|----------|----------|
| **DEMO_MODE** | `true` | `false` |
| **数据库写入** | ❌ 模拟数据 | ✅ 真实写入 |
| **用户注册** | 返回固定用户 | 真实注册 |
| **数据持久化** | ❌ 否 | ✅ 是 |
| **适用场景** | 演示、原型验证 | 生产环境、真实使用 |

## 🔐 环境变量

脚本会自动设置后端 `.env` 文件中的 `DEMO_MODE` 变量：

- **使用 `--demo` 参数**：`DEMO_MODE=true`
- **不使用 `--demo` 参数**：`DEMO_MODE=false`

## 📋 完整示例

### 示例 1：本地开发（默认）

```bash
./run_server.sh
```

**效果**：
- 前端：http://localhost:3010
- 后端：http://localhost:8010
- 生产模式（真实数据库）
- 自动打开浏览器

### 示例 2：本地 Demo 演示

```bash
./run_server.sh --demo
```

**效果**：
- 前端：http://localhost:3010
- 后端：http://localhost:8010
- Demo 模式（模拟数据）
- 自动打开浏览器

### 示例 3：云端生产部署

```bash
./run_server.sh --mode cloud --frontend-port 80 --backend-port 8000
```

**效果**：
- 前端：http://0.0.0.0:80
- 后端：http://0.0.0.0:8000
- 生产模式（真实数据库）
- 外部可访问

### 示例 4：云端 Demo 演示

```bash
./run_server.sh --mode cloud --demo
```

**效果**：
- 前端：http://0.0.0.0:3010
- 后端：http://0.0.0.0:8010
- Demo 模式（模拟数据）
- 外部可访问

### 示例 5：快速重启（跳过安装）

```bash
./run_server.sh --skip-install
```

**效果**：
- 跳过依赖安装
- 快速启动服务

## 🛑 停止服务

按 `Ctrl+C` 停止所有服务。

脚本会自动清理：
- 所有启动的进程
- PID 文件
- 端口信息文件

## 📝 注意事项

1. **首次运行**：不要使用 `--skip-install`，需要安装依赖
2. **云端部署**：建议使用 `--mode cloud` 以获得更好的性能
3. **Demo 模式**：适合演示和测试，不会写入真实数据
4. **生产模式**：默认模式，所有操作都会写入真实数据库
5. **端口占用**：脚本会自动检测并终止占用端口的进程

## 🔍 故障排查

### 问题 1：端口被占用

**解决方案**：
```bash
# 脚本会自动处理，或手动指定其他端口
./run_server.sh --frontend-port 8080 --backend-port 9000
```

### 问题 2：依赖安装失败

**解决方案**：
```bash
# 手动安装依赖
cd backend && pip install -r requirements.txt
cd ../frontend && pnpm install
```

### 问题 3：Python 版本过低

**要求**：Python 3.11+（通过 `uv` 管理运行环境）

**解决方案**：升级 Python 版本

### 问题 4：Node.js 版本过低

**要求**：Node.js 20+

**解决方案**：升级 Node.js 版本

## 📚 相关文档

- [后端 API 文档](http://localhost:8010/docs)
- [项目 README](../README.md)
- [开发规范](./development/)

## 💡 最佳实践

1. **本地开发**：使用默认配置 `./run_server.sh`
2. **演示展示**：使用 `./run_server.sh --demo`
3. **云端部署**：使用 `./run_server.sh --mode cloud`
4. **快速重启**：使用 `./run_server.sh --skip-install`
5. **调试后端**：使用 `./run_server.sh --only backend`
6. **调试前端**：使用 `./run_server.sh --only frontend`
