# Session 会话管理学习笔记

OpenAI Agents SDK 提供内置会话管理，自动维护对话历史，无需在多轮对话之间手动处理 `to_input_list()`。

---

## 1. Session 基本概念

### 1.1 工作原理

```text
Runner.run(..., session=session)
  ├─ 运行前：自动加载该 session 的历史
  ├─ 运行中：生成新内容（用户输入、助手回复、工具调用等）
  └─ 运行后：自动保存新内容到 session

下次 Runner.run(..., session=session)
  └─ 历史已自动包含，无需手动传递
```

**关键点：**
- ✅ 自动管理对话历史
- ✅ 无需手动调用 `to_input_list()`
- ✅ 适合聊天应用、多轮对话

### 1.2 Session vs 手动管理

**不用 Session（手动管理）：**

```python
result1 = await Runner.run(agent, "你好，我叫张三")
history = result1.to_input_list()
result2 = await Runner.run(agent, history + [{"role": "user", "content": "我叫什么名字？"}])
```

**用 Session（自动管理）：**

```python
session = SQLiteSession("user_123")
result1 = await Runner.run(agent, "你好，我叫张三", session=session)
result2 = await Runner.run(agent, "我叫什么名字？", session=session)  # 自动有历史
```

---

## 2. SQLiteSession

最简单的会话实现，基于 SQLite 存储。

### 2.1 内存 Session

```python
from agents import SQLiteSession

# 内存存储（进程结束后丢失）
session = SQLiteSession("user_123")

result = await Runner.run(agent, "你好", session=session)
```

**特点：**
- 存储在内存中
- 进程结束后丢失
- 适合临时对话、调试

### 2.2 文件 Session

```python
# 持久化到文件
session = SQLiteSession("user_123", "conversations.db")

result = await Runner.run(agent, "你好", session=session)
```

**特点：**
- 持久化到 SQLite 文件
- 进程重启后仍可用
- 适合生产环境

### 2.3 多 Session 隔离

```python
session_alice = SQLiteSession("user_alice", "conversations.db")
session_bob = SQLiteSession("user_bob", "conversations.db")

# 两个 session 完全隔离
await Runner.run(agent, "我喜欢足球", session=session_alice)
await Runner.run(agent, "我喜欢游泳", session=session_bob)
```

**验证结果：**

```text
【Alice】我刚才说我喜欢什么？
助手: 你刚才告诉我 **你喜欢足球**

【Bob】我刚才说我喜欢什么？
助手: 你刚才说 **"我喜欢游泳"**
```

### 2.4 Session 操作

```python
# 获取所有历史
items = await session.get_items()

# 手动添加消息
await session.add_items([
    {"role": "user", "content": "你好"},
    {"role": "assistant", "content": "你好啊"}
])

# 弹出最后一条（用于撤销、更正）
last_item = await session.pop_item()

# 清空所有历史
await session.clear_session()
```

**使用场景：**
- `pop_item()`: 撤销、更正对话
- `clear_session()`: "开始新对话"
- `add_items()`: 导入历史、测试

---

## 3. SQLAlchemySession

使用 SQLAlchemy 作为底层存储，支持 PostgreSQL、MySQL、SQLite 等所有 SQLAlchemy 数据库。

### 3.1 from_url() 快速开始

```python
from agents.extensions.memory.sqlalchemy_session import SQLAlchemySession

# 内存 SQLite
session = SQLAlchemySession.from_url(
    "user-123",
    url="sqlite+aiosqlite:///:memory:",
    create_tables=True,
)

# 文件 SQLite
session = SQLAlchemySession.from_url(
    "user-123",
    url="sqlite+aiosqlite:///conversations.db",
    create_tables=True,
)
```

### 3.2 使用现有 AsyncEngine

```python
from sqlalchemy.ext.asyncio import create_async_engine

# 创建 AsyncEngine
engine = create_async_engine(
    "sqlite+aiosqlite:///conversations.db",
    pool_size=20,
    max_overflow=10,
)

# 使用现有 engine
session = SQLAlchemySession(
    "user-456",
    engine=engine,
    create_tables=True,
)

result = await Runner.run(agent, "你好", session=session)

await engine.dispose()
```

### 3.3 生产环境配置

```python
# 开发：SQLite
engine = create_async_engine("sqlite+aiosqlite:///dev.db")

# 生产：PostgreSQL
engine = create_async_engine(
    "postgresql+asyncpg://user:pass@db.example.com/agents",
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,  # 检测连接有效性
)

# 代码完全不变
session = SQLAlchemySession("user_123", engine=engine, create_tables=True)
```

**支持的数据库：**
- PostgreSQL: `postgresql+asyncpg://...`
- MySQL: `mysql+aiomysql://...`
- SQLite: `sqlite+aiosqlite:///path/to/db.sqlite`

### 3.4 SQLiteSession vs SQLAlchemySession

| 特性 | SQLiteSession | SQLAlchemySession |
|------|--------------|-------------------|
| 易用性 | ⭐⭐⭐⭐⭐ 简单直接 | ⭐⭐⭐⭐ 需要 SQLAlchemy |
| 性能 | ⭐⭐⭐⭐ 轻量 | ⭐⭐⭐⭐ 连接池优化 |
| 扩展性 | ⭐⭐ 只支持 SQLite | ⭐⭐⭐⭐⭐ 所有 SQLAlchemy DB |
| 生产级 | ⭐⭐⭐ 单机/小规模 | ⭐⭐⭐⭐⭐ 多实例/大规模 |
| 集成性 | ⭐⭐ 独立 | ⭐⭐⭐⭐⭐ 复用现有 engine |

**使用建议：**
- 调试、单机、小规模 → `SQLiteSession`
- 生产、多实例、已有 SQLAlchemy 应用 → `SQLAlchemySession`

---

## 4. AdvancedSQLiteSession

SQLiteSession 的增强版，提供用量统计、对话分支、结构化查询等高级功能。

### 4.1 核心功能

**1. 用量统计（⭐⭐⭐ 高价值）**
- 按轮次追踪 token 用量
- 区分输入/输出 tokens
- 包含详细 JSON 明细（reasoning_tokens、cached_tokens）

**2. 对话分支（⭐ 低优先级）**
- 从任意用户消息创建"平行宇宙"对话
- 适合 A/B 测试、探索不同策略
- 一般业务场景用不上

**3. 结构化查询（⭐⭐⭐ 高价值）**
- 按轮次组织对话
- 统计工具使用情况
- 分析对话行为模式

### 4.2 用量统计

#### 初始化

```python
from agents.extensions.memory import AdvancedSQLiteSession

session = AdvancedSQLiteSession(
    session_id="user_123",
    db_path="conversations.db",
    create_tables=True,
)
```

#### 记录用量

```python
result = await Runner.run(agent, "你好", session=session)

# 🔥 关键：必须手动调用
await session.store_run_usage(result)
```

**注意：**
- 每次 `Runner.run()` 后必须调用 `store_run_usage()`
- 不调用就不会记录用量

#### 查询总用量

```python
# 查询 session 总用量
usage = await session.get_session_usage()
print(f"总请求数: {usage['requests']}")
print(f"总 tokens: {usage['total_tokens']}")
print(f"输入 tokens: {usage['input_tokens']}")
print(f"输出 tokens: {usage['output_tokens']}")
print(f"总轮数: {usage['total_turns']}")

# 查询特定分支的用量
branch_usage = await session.get_session_usage(branch_id="main")
```

#### 查询每轮用量

```python
# 查询所有轮次的用量
turn_usage = await session.get_turn_usage()
for turn_data in turn_usage:
    turn = turn_data['user_turn_number']
    tokens = turn_data['total_tokens']
    input_tokens = turn_data['input_tokens']
    output_tokens = turn_data['output_tokens']
    print(f"第{turn}轮: 总 {tokens} tokens (输入 {input_tokens} + 输出 {output_tokens})")

# 查询特定轮次
turn_2_usage = await session.get_turn_usage(user_turn_number=2)
```

**验证结果示例：**

```text
第1轮: 88 tokens (输入 8 + 输出 80)
第2轮: 238 tokens (输入 23 + 输出 215)
第3轮: 309 tokens (输入 53 + 输出 256)

平均每轮: 211.7 tokens
```

**关键发现：**
- 随着对话历史增长，输入 tokens 逐渐增加（8 → 23 → 53）
- 可用于分析成本增长趋势
- 适合优化 prompt 长度

#### 详细用量信息（JSON 明细）

```python
turn_usage = await session.get_turn_usage()
turn_data = turn_usage[0]

# 输入明细
if turn_data.get('input_tokens_details'):
    print(turn_data['input_tokens_details'])
    # {"cached_tokens": 0}

# 输出明细
if turn_data.get('output_tokens_details'):
    print(turn_data['output_tokens_details'])
    # {"reasoning_tokens": 93}
```

**关键字段：**
- `reasoning_tokens`: DeepSeek 的思考过程 tokens
- `cached_tokens`: 缓存的 tokens（如果 API 支持）

### 4.3 工具调用用量对比

**验证结果：**

```text
第1轮（无工具）: 371 tokens, 1 次请求
第2轮（有工具）: 976 tokens, 2 次请求  ← 工具调用导致请求数增加
```

**关键发现：**
- ✅ 工具调用会产生多次请求（function calling → tool result → final response）
- ✅ 工具调用的用量明显更高（976 vs 371 tokens）
- ✅ `requests` 字段可用于判断是否有工具调用

### 4.4 对话分支

#### 创建分支

```python
# 从第2轮创建分支
branch_id = await session.create_branch_from_turn(2, branch_name="alternative")

# 从包含特定内容的消息创建分支
branch_id = await session.create_branch_from_content("天气", branch_name="weather_focus")
```

#### 切换分支

```python
# 切换到主分支
await session.switch_to_branch("main")

# 切换到其他分支
await session.switch_to_branch(branch_id)
```

#### 列出所有分支

```python
branches = await session.list_branches()
for branch in branches:
    current = " (current)" if branch["is_current"] else ""
    print(f"{branch['branch_id']}: {branch['user_turns']} 轮, {branch['message_count']} 消息{current}")
```

#### 删除分支

```python
await session.delete_branch(branch_id, force=True)  # force=True 允许删除当前分支
```

#### 分支用量隔离

```text
主分支用量: 496 tokens, 2轮
分支 alternative 用量: 541 tokens, 1轮
```

**关键点：**
- ✅ 不同分支的用量完全独立统计
- ✅ 可用于对比不同对话策略的成本
- ✅ 适合 A/B 测试场景

### 4.5 结构化查询

```python
# 按轮次组织对话
conversation = await session.get_conversation_by_turns()
for turn_num, items in conversation.items():
    print(f"Turn {turn_num}: {len(items)} 条消息")

# 统计工具使用
tool_usage = await session.get_tool_usage()
for tool_name, count, turn in tool_usage:
    print(f"{tool_name}: 在第{turn}轮调用了 {count} 次")

# 查找包含特定内容的轮次
matching_turns = await session.find_turns_by_content("天气")
```

---

## 5. 其他 Session 类型

### 5.1 OpenAI Conversations API Session

使用 OpenAI 托管的对话存储：

```python
from agents import OpenAIConversationsSession

session = OpenAIConversationsSession()

# 恢复之前的对话
# session = OpenAIConversationsSession(conversation_id="conv_123")

result = await Runner.run(agent, "Hello", session=session)
```

**特点：**
- OpenAI 托管存储
- 无需管理自己的数据库
- 适合已依赖 OpenAI 基础设施的应用

### 5.2 EncryptedSession

对静态对话数据进行加密，支持基于 TTL 的自动过期：

```python
from agents.extensions.memory import EncryptedSession, SQLAlchemySession

# 创建底层 session
underlying_session = SQLAlchemySession.from_url(
    "user-123",
    url="postgresql+asyncpg://app:secret@db.example.com/agents",
    create_tables=True,
)

# 包装为加密 session
session = EncryptedSession(
    session_id="user-123",
    underlying_session=underlying_session,
    encryption_key="your-encryption-key",  # 使用安全的密钥
    ttl=600,  # 10 分钟 - 超时的条目会被跳过
)

result = await Runner.run(agent, "Hello", session=session)
```

**特性：**
- 透明加密：自动加密/解密
- 按会话派生密钥：使用 HKDF
- 基于 TTL 的过期：自动跳过过期消息
- 可包装任意 Session

**安全注意事项：**
- 安全存储加密密钥（环境变量、密钥管理服务）
- 所有服务通过 NTP 同步时间（避免时钟漂移）
- 底层 session 仍存储加密数据

---

## 6. 自定义 Session

实现 `SessionABC` 协议即可创建自定义 Session：

```python
from agents.memory.session import SessionABC
from agents.items import TResponseInputItem
from typing import List

class MyCustomSession(SessionABC):
    def __init__(self, session_id: str):
        self.session_id = session_id

    async def get_items(self, limit: int | None = None) -> List[TResponseInputItem]:
        """获取对话历史。"""
        # 实现逻辑
        pass

    async def add_items(self, items: List[TResponseInputItem]) -> None:
        """存储新消息。"""
        pass

    async def pop_item(self) -> TResponseInputItem | None:
        """弹出最后一条。"""
        pass

    async def clear_session(self) -> None:
        """清空所有历史。"""
        pass

# 使用
session = MyCustomSession("my_session")
result = await Runner.run(agent, "Hello", session=session)
```

**适合场景：**
- 接入 Redis
- 接入 Django ORM
- 接入现有后端数据库
- 自定义存储逻辑

---

## 7. 生产部署建议

### 7.1 选型建议

| 场景 | 推荐方案 |
|------|---------|
| 调试、单机 | `SQLiteSession` |
| 生产、多实例、已有 SQLAlchemy | `SQLAlchemySession` |
| 需要用量统计、成本分析 | `AdvancedSQLiteSession` |
| 需要加密、TTL 过期 | `EncryptedSession` |
| 已依赖 OpenAI 基础设施 | `OpenAIConversationsSession` |
| 已有后端存储（Redis/Django） | 自定义 `SessionABC` |

### 7.2 ANIFORCE 推荐架构

```python
# backend/app/config.py
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    settings.DATABASE_URL,  # postgresql+asyncpg://...
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)

# backend/app/services/agent_service.py
from agents.extensions.memory import AdvancedSQLiteSession

def get_agent_session(user_id: str, conversation_id: str):
    session_id = f"{user_id}:{conversation_id}"
    return AdvancedSQLiteSession(
        session_id,
        db_path=f"sqlite+aiosqlite:///{settings.DB_PATH}",
        create_tables=False,  # 表由 Alembic 管理
    )

# 使用
async def run_agent_with_tracking(user_id: str, conv_id: str, input: str):
    session = get_agent_session(user_id, conv_id)
    
    result = await Runner.run(agent, input, session=session)
    
    # 🔥 记录用量
    await session.store_run_usage(result)
    
    # 上报到监控系统
    usage = await session.get_session_usage()
    metrics.record({
        "user_id": user_id,
        "conversation_id": conv_id,
        "total_tokens": usage["total_tokens"],
        "cost_usd": calculate_cost(usage),
    })
    
    return result
```

### 7.3 成本分析示例

```python
# 查询对话总成本
async def get_conversation_cost(session_id: str):
    session = AdvancedSQLiteSession(session_id=session_id)
    usage = await session.get_session_usage()
    
    # DeepSeek 定价示例
    input_cost = usage["input_tokens"] / 1000 * 0.0001
    output_cost = usage["output_tokens"] / 1000 * 0.0002
    
    return {
        "total_tokens": usage["total_tokens"],
        "total_cost_usd": input_cost + output_cost,
        "total_turns": usage["total_turns"],
        "avg_cost_per_turn": (input_cost + output_cost) / usage["total_turns"],
    }

# 按轮次分析成本趋势
async def analyze_cost_trend(session_id: str):
    session = AdvancedSQLiteSession(session_id=session_id)
    turn_usage = await session.get_turn_usage()
    
    trends = []
    for turn_data in turn_usage:
        turn = turn_data["user_turn_number"]
        tokens = turn_data["total_tokens"]
        cost = calculate_cost(turn_data)
        trends.append({
            "turn": turn,
            "tokens": tokens,
            "cost_usd": cost,
        })
    
    return trends

# 监控高成本工具调用
async def monitor_expensive_tools(session_id: str):
    session = AdvancedSQLiteSession(session_id=session_id)
    turn_usage = await session.get_turn_usage()
    
    expensive_turns = []
    for turn_data in turn_usage:
        if turn_data["requests"] > 1:  # 有工具调用
            if turn_data["total_tokens"] > 500:  # 高成本阈值
                expensive_turns.append({
                    "turn": turn_data["user_turn_number"],
                    "tokens": turn_data["total_tokens"],
                    "requests": turn_data["requests"],
                })
    
    return expensive_turns
```

### 7.4 Session 管理最佳实践

**1. Session ID 命名规范**

```python
# 基于用户
session_id = f"user_{user_id}"

# 基于对话
session_id = f"{user_id}:{conversation_id}"

# 基于上下文
session_id = f"support_ticket_{ticket_id}"
```

**2. 清理策略**

```python
# 定期清理旧会话（如 30 天前）
async def cleanup_old_sessions():
    cutoff_date = datetime.now() - timedelta(days=30)
    # 根据 create_at 删除旧记录
```

**3. 不同 Agent 共享 Session**

```python
support_agent = Agent(name="Support")
billing_agent = Agent(name="Billing")
session = SQLiteSession("shared")

# 两个 agent 共享同一个历史
await Runner.run(support_agent, "...", session=session)
await Runner.run(billing_agent, "...", session=session)
```

**4. 多实例部署注意事项**

- ✅ 使用共享数据库（PostgreSQL/MySQL），不要用本地文件
- ✅ 使用 `SQLAlchemySession` 复用应用的 engine
- ✅ 配置合理的连接池大小
- ✅ 考虑数据库读写分离

---

## 8. 调试脚本

所有调试脚本位于 `notebooks/05-session/`：

| 脚本 | 验证内容 |
|------|---------|
| `260702_01_session_management_debug.py` | SQLiteSession 基础功能、多 session 隔离、session 操作 |
| `260702_02_sqlalchemy_session_debug.py` | SQLAlchemySession 的 SQLite/PostgreSQL 配置、多实例支持 |
| `260702_03_advanced_session_usage_debug.py` | AdvancedSQLiteSession 用量统计、按轮次分析、工具调用成本 |

---

## 9. 关键总结

### Session 的核心价值

1. **自动历史管理**
   - 无需手动 `to_input_list()`
   - 自动加载和保存历史
   - 简化多轮对话代码

2. **用量统计（AdvancedSQLiteSession）**
   - 按轮次追踪 token 用量
   - 区分输入/输出/工具调用成本
   - 支持成本分析和优化

3. **多租户隔离**
   - 同一数据库，不同 session_id 完全隔离
   - 适合多用户、多对话场景

4. **灵活扩展**
   - SQLite → PostgreSQL 只需换 URL
   - 实现 `SessionABC` 可接入任意存储

### 必须记住的

1. **SQLiteSession vs SQLAlchemySession**
   - 调试/小规模 → SQLiteSession
   - 生产/多实例 → SQLAlchemySession

2. **AdvancedSQLiteSession 用量统计**
   - 每次 `Runner.run()` 后必须调用 `store_run_usage(result)`
   - 用 `get_session_usage()` 查询总用量
   - 用 `get_turn_usage()` 分析每轮成本

3. **生产部署**
   - 使用共享数据库（PostgreSQL/MySQL）
   - 复用应用的 SQLAlchemy engine
   - 配置连接池和监控

4. **成本优化**
   - 监控输入 tokens 增长趋势
   - 分析高成本工具调用
   - 设置成本告警阈值
