# ANIFORCE 部署指南

本文档介绍如何使用 Nginx 反向代理统一部署 ANIFORCE 前后端服务。

## 架构说明

```
用户请求 → Nginx (端口 80) → 前端服务 (端口 3010)
                            → 后端 API (端口 8010)
```

### 服务组件

1. **Nginx 反向代理** - 统一入口，负责请求分发
2. **后端服务** - FastAPI (默认端口: 8010)
3. **前端服务** - Vite (默认端口: 3010)

### 路由规则

- `/` - 前端应用
- `/api/*` - 后端 API
- `/docs` - API 文档 (Swagger UI)
- `/redoc` - API 文档 (ReDoc)
- `/health` - 健康检查端点

## 快速开始

### 1. 完整部署（推荐）

启动所有服务（Nginx + 前端 + 后端）：

```bash
./deploy_server.sh
```

访问地址：http://localhost

### 2. 停止所有服务

```bash
./undeploy_server.sh
```

## 高级用法

### 部署选项

```bash
# 本地开发模式（默认）
./deploy_server.sh --mode local

# 云端生产模式
./deploy_server.sh --mode cloud --skip-install

# 启用 Demo 模式
./deploy_server.sh --demo

# 自定义端口
./deploy_server.sh --nginx-port 8080 --frontend-port 3000 --backend-port 8000
```

### 部分部署

```bash
# 仅启动后端
./deploy_server.sh --only backend

# 仅启动前端
./deploy_server.sh --only frontend

# 仅启动 Nginx（前提：前后端已在运行）
./deploy_server.sh --only nginx
```

### 部分停止

```bash
# 仅停止 Nginx
./undeploy_server.sh --only nginx

# 仅停止后端
./undeploy_server.sh --only backend

# 仅停止前端
./undeploy_server.sh --only frontend
```

## 配置说明

### Nginx 配置

Nginx 配置文件位于 `nginx.conf`，包含以下特性：

- **反向代理** - 将请求转发到前后端服务
- **WebSocket 支持** - 支持 Vite HMR 和实时通信
- **负载均衡** - 使用 keepalive 连接池
- **健康检查** - `/health` 端点
- **日志记录** - 访问日志和错误日志

### 端口配置

默认端口配置：

| 服务 | 端口 | 说明 |
|------|------|------|
| Nginx | 80 | 统一入口 |
| 前端 | 3010 | Vite 开发服务器 |
| 后端 | 8010 | FastAPI 服务 |

可通过命令行参数自定义端口。

### 环境变量

部署脚本会自动配置以下环境变量：

- `FRONTEND_BASE_URL` - 前端访问地址
- `BACKEND_BASE_URL` - 后端访问地址
- `DEMO_MODE` - Demo 模式开关

## 故障排查

### Nginx 启动失败

**问题**: 端口 80 被占用

**解决方案**:
```bash
# 使用其他端口
./deploy_server.sh --nginx-port 8080

# 或停止占用端口的进程
sudo lsof -ti :80 | xargs sudo kill -9
```

### 权限问题

**问题**: Nginx 需要 root 权限监听 80 端口

**解决方案**:
```bash
# 使用非特权端口
./deploy_server.sh --nginx-port 8080

# 或使用 sudo（不推荐）
sudo ./deploy_server.sh
```

### 服务无法访问

**检查步骤**:

1. 检查服务状态
```bash
# 检查端口占用
lsof -i :80
lsof -i :3010
lsof -i :8010

# 检查 Nginx 状态
nginx -t
```

2. 查看日志
```bash
# Nginx 日志
tail -f /tmp/aniforce_access.log
tail -f /tmp/aniforce_error.log

# 后端日志
cd backend && tail -f *.log

# 前端日志（控制台输出）
```

3. 健康检查
```bash
curl http://localhost/health
curl http://localhost:8010/docs
curl http://localhost:3010
```

## 与原有脚本的区别

### run_server.sh vs deploy_server.sh

| 特性 | run_server.sh | deploy_server.sh |
|------|---------------|------------------|
| Nginx 支持 | ✗ | ✓ |
| 统一入口 | ✗ | ✓ (通过 Nginx) |
| 前后端直连 | ✓ | ✓ (可选) |
| 生产部署 | 部分支持 | 完全支持 |

### 建议使用场景

- **开发调试**: 使用 `run_server.sh`（直接访问前后端）
- **生产部署**: 使用 `deploy_server.sh`（通过 Nginx 统一入口）
- **演示/测试**: 使用 `deploy_server.sh --demo`

## 生产部署建议

### 1. 云端部署

```bash
# 设置云端 IP
export CLOUD_IP=your-server-ip

# 部署
./deploy_server.sh --mode cloud --skip-install
```

### 2. HTTPS 配置

修改 `nginx.conf` 添加 SSL 配置：

```nginx
server {
    listen 443 ssl;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    # ... 其他配置
}
```

### 3. 性能优化

- 启用 Nginx 缓存
- 配置 gzip 压缩
- 调整 worker 进程数
- 使用 CDN 加速静态资源

### 4. 监控和日志

- 配置日志轮转
- 集成监控系统（如 Prometheus）
- 设置告警规则

## 常见问题

**Q: 如何查看当前部署配置？**

A: 查看 `.deploy_config` 文件：
```bash
cat .deploy_config
```

**Q: 如何重启服务？**

A: 先停止再启动：
```bash
./undeploy_server.sh
./deploy_server.sh
```

**Q: 如何只重启 Nginx？**

A: 
```bash
./undeploy_server.sh --only nginx
./deploy_server.sh --only nginx
```

**Q: 开发时是否必须使用 Nginx？**

A: 不必须。开发时可以直接使用 `run_server.sh`，仅在需要测试完整部署流程时使用 `deploy_server.sh`。

## 维护命令

```bash
# 查看 Nginx 配置
nginx -t -c /path/to/nginx.conf

# 重载 Nginx 配置（不中断服务）
nginx -s reload

# 查看服务进程
ps aux | grep nginx
ps aux | grep uvicorn
ps aux | grep vite

# 清理所有临时文件
rm -f .server_pids .server_ports .deploy_config .nginx_runtime.conf
```

## 支持

如有问题，请查看：
- 项目 README.md
- 后端文档: http://localhost/docs
- 日志文件: /tmp/aniforce_*.log
