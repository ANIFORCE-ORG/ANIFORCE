# Redis Agent Stream

Redis 只承载短期 Agent 增量事件，业务事实仍写入 SQLite/生产数据库。

## 本地启动

```bash
redis-server \
  --bind 127.0.0.1 \
  --protected-mode yes \
  --port 6379 \
  --save '' \
  --appendonly no \
  --daemonize yes \
  --pidfile "$PWD/logs/run/redis.pid" \
  --logfile "$PWD/logs/redis_260711.log" \
  --dir "$PWD/logs/run"
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

Redis 不可用时，Run 继续执行和落库，SSE 降级为耐久状态与最终结果。

## Linux 生产扩展

安装 Redis Community Edition 后设置 `REDIS_URL` 即可，应用协议无需修改。单机部署绑定 `127.0.0.1`；未来服务拆机时使用内网 Redis 或托管 Redis，并配置认证、TLS、内存上限和监控。
