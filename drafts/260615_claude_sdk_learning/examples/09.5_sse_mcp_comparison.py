#!/usr/bin/env python
"""第 9.5 章：外部 SSE MCP Server 验证

对比 SDK in-process MCP 和外部 SSE MCP Server：

AiToEarn 的 MCP 架构：
- NestJS + @Tool 装饰器
- SSE (Server-Sent Events) 传输层
- HTTP POST /messages 端点接收请求
- 支持鉴权（通过 NestJS Guards）
- 会话隔离（通过 sessionId）

验证目标：
1. 配置 Claude SDK 连接到外部 SSE MCP server
2. 测试鉴权机制（headers）
3. 测试工具调用和响应
4. 对比 SDK MCP vs SSE MCP 的性能和复杂度
"""

import asyncio
import json
import sys
from pathlib import Path

# 添加 SDK 到 sys.path
sdk_path = Path(__file__).resolve().parents[3] / "resources" / "claude-agent-sdk-python" / "src"
if str(sdk_path) not in sys.path:
    sys.path.insert(0, str(sdk_path))

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
from claude_agent_sdk.types import (
    AssistantMessage,
    Message,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)

# 测试统计
test_stats = {
    "sdk_mcp_called": 0,
    "sse_mcp_called": 0,
    "sdk_mcp_success": 0,
    "sse_mcp_success": 0,
    "sdk_mcp_error": 0,
    "sse_mcp_error": 0,
}


async def test_sdk_mcp(test_name: str, prompt: str):
    """测试 SDK in-process MCP（作为基准）"""
    print(f"\n{'='*60}")
    print(f"测试 SDK MCP: {test_name}")
    print(f"Prompt: {prompt}")
    print(f"{'='*60}\n")

    from claude_agent_sdk import create_sdk_mcp_server, tool

    @tool("add", "Add two numbers", {"a": float, "b": float})
    async def add_numbers(args):
        result = args["a"] + args["b"]
        return {"content": [{"type": "text", "text": f"Result: {result}"}]}

    calculator = create_sdk_mcp_server(name="calc", version="1.0.0", tools=[add_numbers])

    options = ClaudeAgentOptions(
        mcp_servers={"calc": calculator},
        allowed_tools=["mcp__calc__add"],
    )

    test_stats["sdk_mcp_called"] += 1

    try:
        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt)

            async for msg in client.receive_response():
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            print(f"Claude: {block.text[:200]}...")
                        elif isinstance(block, ToolUseBlock):
                            print(f"[Tool Call] {block.name}")
                elif isinstance(msg, ResultMessage):
                    if not msg.is_error:
                        test_stats["sdk_mcp_success"] += 1
                    else:
                        test_stats["sdk_mcp_error"] += 1
                    print(f"Result: {msg.stop_reason}")
    except Exception as e:
        test_stats["sdk_mcp_error"] += 1
        print(f"Error: {e}")


async def test_sse_mcp_concept():
    """演示 SSE MCP 的配置概念（不实际连接）"""
    print(f"\n{'='*60}")
    print("SSE MCP Server 配置说明")
    print(f"{'='*60}\n")

    # SSE MCP Server 的配置格式
    sse_mcp_config = {
        "type": "sse",
        "url": "http://localhost:3000/api/mcp/sse",  # SSE 连接端点
        "headers": {
            "Authorization": "Bearer <token>",  # 鉴权 token
            "X-User-Id": "<user-id>",  # 用户 ID
        },
    }

    print("SSE MCP Server 配置格式:")
    print(json.dumps(sse_mcp_config, indent=2))

    print("\nAiToEarn MCP 架构:")
    print("1. SSE 传输层（持久连接）")
    print("   - GET /api/mcp/sse → 建立 SSE 连接")
    print("   - POST /api/mcp/messages?sessionId=xxx → 发送请求")
    print("")
    print("2. 鉴权机制")
    print("   - NestJS Guards 拦截请求")
    print("   - 从 headers 提取 user context")
    print("   - @Tool 方法内部调用 getUser() 获取用户信息")
    print("")
    print("3. 工具注册")
    print("   - @Tool 装饰器标记方法")
    print("   - McpRegistryService 自动发现并注册")
    print("   - Zod schema 定义参数验证")
    print("")
    print("4. 会话隔离")
    print("   - 每个 SSE 连接有独立 sessionId")
    print("   - transports Map 存储活跃连接")
    print("   - mcpServers Map 存储 MCP Server 实例")

    print("\n优势:")
    print("✅ 支持多语言（不限 Python）")
    print("✅ 独立部署（服务解耦）")
    print("✅ 鉴权和租户隔离（通过 Guards）")
    print("✅ 多租户会话管理")
    print("")
    print("劣势:")
    print("❌ 需要外部服务（部署复杂）")
    print("❌ 网络延迟（IPC 开销）")
    print("❌ 需要 sticky sessions（transports 在内存）")

    print("\nSDK in-process MCP 对比:")
    print("优势:")
    print("✅ 单进程部署（简单）")
    print("✅ 无网络延迟")
    print("✅ 直接访问应用状态")
    print("")
    print("劣势:")
    print("❌ 仅 Python（语言绑定）")
    print("❌ 不能独立扩展")
    print("❌ 鉴权需要自己实现（通过 Hooks）")


async def demonstrate_aitoearn_mcp_structure():
    """演示 AiToEarn MCP 的代码结构"""
    print(f"\n{'='*60}")
    print("AiToEarn MCP 代码示例")
    print(f"{'='*60}\n")

    twitter_tool_example = '''
# 1. 定义工具（NestJS Controller + @Tool 装饰器）

@Injectable()
export class TwitterMcpController {
  constructor(private readonly twitterService: TwitterService) {}

  @Tool({
    name: 'searchTweets',
    description: 'Search recent Twitter/X tweets',
    parameters: searchTweetsSchema,  // Zod schema
  })
  async searchTweets(params: z.infer<typeof searchTweetsSchema>) {
    const user = getUser()  // 从请求上下文获取用户（鉴权后）
    return toYamlTextResult(
      await this.twitterService.searchTweets(user.id, params.accountId, params)
    )
  }
}
'''

    nest_mcp_module = '''
# 2. 配置 MCP Module（应用启动时）

@Module({
  imports: [
    McpModule.forRoot({
      name: 'aitoearn-mcp',
      version: '1.0.0',
      transport: [McpTransportType.SSE],  // 启用 SSE 传输
      sseEndpoint: 'sse',
      messagesEndpoint: 'messages',
      guards: [JwtAuthGuard],  // 鉴权守卫
    }),
  ],
  controllers: [TwitterMcpController],  // 注册工具 Controller
})
export class AppModule {}
'''

    claude_sdk_config = '''
# 3. Claude SDK 连接配置（Python 客户端）

from claude_agent_sdk import ClaudeAgentOptions

options = ClaudeAgentOptions(
    mcp_servers={
        "aitoearn": {
            "type": "sse",
            "url": "http://localhost:3000/api/mcp/sse",
            "headers": {
                "Authorization": "Bearer <token>",
                "X-Tenant-Id": "tenant_001",
            }
        }
    },
    allowed_tools=[
        "mcp__aitoearn__searchTweets",
        "mcp__aitoearn__listHomeTimeline",
    ],
)
'''

    print("=" * 60)
    print("1. 定义工具（NestJS + @Tool）")
    print("=" * 60)
    print(twitter_tool_example)

    print("=" * 60)
    print("2. 配置 MCP Module")
    print("=" * 60)
    print(nest_mcp_module)

    print("=" * 60)
    print("3. Claude SDK 连接配置")
    print("=" * 60)
    print(claude_sdk_config)


async def main():
    """主测试流程"""

    print("第 9.5 章：外部 SSE MCP Server 对比")
    print("=" * 80)

    # 测试 SDK in-process MCP（基准）
    await test_sdk_mcp("SDK in-process MCP 基准测试", "Calculate 15 + 27 using the add tool")

    # 演示 SSE MCP 配置概念
    await test_sse_mcp_concept()

    # 演示 AiToEarn MCP 代码结构
    await demonstrate_aitoearn_mcp_structure()

    # 输出统计
    print("\n" + "=" * 80)
    print("测试统计:")
    print(json.dumps(test_stats, indent=2, ensure_ascii=False))

    # 架构对比总结
    print("\n" + "=" * 80)
    print("架构对比总结:")
    print("=" * 80)

    comparison = {
        "SDK_in_process_MCP": {
            "部署": "单进程",
            "性能": "无 IPC 开销",
            "语言": "仅 Python",
            "鉴权": "需要 Hooks 实现",
            "扩展性": "绑定到主应用",
            "适用场景": "Python 应用、业务逻辑封装",
        },
        "SSE_MCP_Server": {
            "部署": "独立服务",
            "性能": "网络延迟",
            "语言": "任意语言",
            "鉴权": "NestJS Guards",
            "扩展性": "独立扩展",
            "适用场景": "多语言、服务解耦、多租户",
        },
    }

    print(json.dumps(comparison, indent=2, ensure_ascii=False))

    # ANIFORCE 建议
    print("\n" + "=" * 80)
    print("ANIFORCE 迁移建议:")
    print("=" * 80)
    print(
        """
方案 1: 纯 SDK in-process MCP（推荐快速迁移）
- 优势: 部署简单，无外部依赖，性能最佳
- 劣势: 绑定 Python，无法独立扩展
- 适合: 快速原型验证、单体应用

方案 2: 混合架构（推荐生产）
- 核心业务工具: SDK in-process MCP（文件、数据库、配置）
- 外部服务工具: SSE MCP Server（Twitter、Email、第三方 API）
- 优势: 平衡性能和扩展性
- 适合: 生产环境、多团队协作

方案 3: 纯 SSE MCP Server（长期演进）
- 复用 AiToEarn 的 nest-mcp 库
- 所有工具通过 SSE MCP 暴露
- 优势: 服务解耦，独立扩展，多语言支持
- 劣势: 部署复杂，需要 sticky sessions
- 适合: 微服务架构、多租户 SaaS

推荐路线:
Phase 1: SDK in-process MCP（快速验证）
Phase 2: 混合架构（稳定生产）
Phase 3: 纯 SSE MCP（规模化）
"""
    )

    # 保存结果
    output_dir = Path("drafts/260615_claude_sdk_learning/outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "test_stats": test_stats,
        "comparison": comparison,
        "aitoearn_mcp_architecture": {
            "transport": "SSE (Server-Sent Events)",
            "endpoints": {
                "sse_connection": "GET /api/mcp/sse",
                "messages": "POST /api/mcp/messages?sessionId=xxx",
            },
            "authentication": "NestJS Guards + getUser() context",
            "tool_registration": "@Tool decorator + McpRegistryService",
            "session_isolation": "sessionId + transports Map",
        },
    }

    output_file = output_dir / "09.5_sse_mcp_comparison.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n结果已保存到: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
