# Redis Agent Stream

Redis 只承载短期 Agent 增量事件，业务事实仍写入 SQLite/生产数据库。

## 本地启动

`run_server.sh` 和 `scripts/start-dev.sh` 会在启动 Backend 前执行
`scripts/ensure-redis.sh`。检查逻辑如下：

- Redis 已可用：继续启动。
- 本机 Redis 未运行：优先启动 `redis-server.service`，无 systemd 时启动独立 Redis 进程。
- 远程 Redis 不可达或本机 Redis 无法启动：立即终止，避免实时事件静默丢失。

Ubuntu/Debian 首次安装：

```bash
sudo apt-get install redis-server redis-tools
sudo systemctl enable --now redis-server
```

也可以单独执行前置检查：

```bash
scripts/ensure-redis.sh backend/.env logs
```

配置：

```env
REDIS_URL=redis://127.0.0.1:6379/0
AGENT_EVENT_STREAM_TTL_SECONDS=900
AGENT_EVENT_STREAM_MAX_LENGTH=5000
```

检查和停止：

```bash
redis-cli ping
redis-cli shutdown nosave
```

## 数据边界

Redis Stream 保存 15 分钟并限长，只包含：

- reasoning/text delta
- tool called/output
- Agent 状态变化
- run started/completed/error/aborted/requires_action

SQLite/生产数据库保存：

- Run 和审批状态
- 最终 Assistant Message
- 工具最终结果
- usage 和错误

运行期间 Redis 突发不可用时，Run 仍会执行和落库，SSE 降级为耐久状态与最终结果；标准启动脚本会在启动前阻止 Redis 不可用的服务栈上线。

## Linux 生产扩展

安装 Redis Community Edition 后设置 `REDIS_URL` 即可，应用协议无需修改。单机部署绑定 `127.0.0.1`；未来服务拆机时使用内网 Redis 或托管 Redis，并配置认证、TLS、内存上限和监控。
