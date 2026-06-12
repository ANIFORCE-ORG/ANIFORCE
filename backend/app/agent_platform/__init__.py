"""
ANIFORCE Agent Platform

工业级 Agent 平台基建，逻辑独立，未来可拆分为独立服务。

核心模块：
- models: AgentTask / AgentTaskEvent / AgentTaskStatus
- errors: 统一错误码和异常类
- events: 事件定义和转换
- runtime: AgentRuntime（封装 OpenAI SDK）
- adapters: SDK 适配层
- repositories: 数据访问层
- mcp: MCP 工具注册
- queue: 异步任务队列
- skills: Skill 系统
- sessions: Session 管理
"""

__version__ = "0.1.0"
