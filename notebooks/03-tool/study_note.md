# 工具调用运行时调试学习笔记

## 目录结构

```text
notebooks/03-runtime/
├── 260701_01_responses_model_settings_debug.py
├── 260701_02_local_function_tool_debug.py
├── 260701_03_shelltool_local_debug.py
├── 260701_04_tool_output_image_file_debug.py
├── 260701_05_function_tool_timeout_debug.py
└── 260701_06_function_tool_error_handling_debug.py
```

---

## 1. OpenAI Responses ModelSettings 高级参数

### 关键参数说明

```python
ModelSettings(
    parallel_tool_calls=False,      # 禁止同一轮并行调用多个工具
    truncation="auto",              # 上下文超限时自动截断最早内容
    store=False,                    # 不让服务端保存 response
    context_management=[...],       # 服务端上下文压缩
    prompt_cache_retention="24h",   # 延长 prompt 前缀缓存保留时间
    top_logprobs=2,                 # 返回 top 2 候选 token 概率
)
```

#### parallel_tool_calls

- `True`：模型可以一轮里并行调用多个工具
- `False`：模型一次只调用一个工具，更容易控流程、调试、做审批
- 对 ANIFORCE 建议：关键业务写操作设为 `False`，避免并发工具调用造成状态冲突

#### truncation="auto"

- 当上下文太长快超限时，允许 Responses API 自动截断最早的上下文项
- 好处：长对话不容易因为 token 超限失败
- 风险：早期上下文可能被丢掉，模型可能忘记旧信息
- 建议：重要业务状态不能只靠上下文，应该放 backend/session_state/workspace

#### store

- `store=True`：服务端保存 response，后续可以基于 response id 做检索、续接
- `store=False`：服务端不保存，更偏隐私/无状态/零数据保留风格
- 风险：依赖 response id 的后续流程不能用，需要自己在本地或 backend 保存必要状态
- 对 ANIFORCE：如果生产注重数据隐私，用 `False`；但要确保 backend 自己保存消息、run、workspace 状态

#### context_management

```python
context_management=[{"type": "compaction", "compact_threshold": 200000}]
```

- 开启 Responses API 的服务端上下文压缩
- 当渲染后的上下文超过 `compact_threshold` 时，服务端可以把旧上下文压缩成摘要项
- 这是服务端压缩，不等于 SDK 本地 session compaction
- 好处：长任务上下文更稳定，不容易爆 token
- 风险：压缩摘要可能损失细节
- 建议：重要业务事实仍应放 backend，不要只依赖压缩后的模型上下文

#### prompt_cache_retention

- 让服务端更长时间保留可复用的 prompt 前缀缓存
- `"24h"` 表示缓存前缀尽量保留 24 小时
- 好处：重复系统 prompt、工具说明、长 instructions 时，可能降低延迟和成本
- 适合：固定 Agent instructions、固定工具说明、固定 skill index
- 是否生效取决于模型/API/provider 支持

**不开 ≠ 不缓存**：

```text
不设置 prompt_cache_retention：仍然可能有默认 prompt caching
设置 prompt_cache_retention="24h"：明确告诉 API 希望保留 24 小时
```

#### top_logprobs

- 请求输出 token 的候选概率信息
- 返回每个输出 token 的 top N 候选 token 及概率
- 用于调试模型置信度、分析输出稳定性
- 会增加响应 payload 大小
- 建议：生产不默认开，只在调试、评估、质量分析时开

---

## 2. 本地运行时工具 (Local Function Tool)

### 基本用法

```python
from agents import function_tool
from typing import Annotated

@function_tool
def fetch_project_brief(
    project_id: Annotated[str, "项目 ID，例如 P001"],
) -> str:
    """从 backend 或本地读取项目简介和营销目标。"""
    return f"[fetch_project_brief] 项目 {project_id} 简介..."

agent = Agent(
    tools=[fetch_project_brief, ...],
    ...
)
```

### description 来源

工具的 `description` 自动从函数 docstring 提取：

```python
@function_tool
def analyze_material_performance(material_id: str) -> str:
    """分析素材投放表现：CTR、转化率、花费等。"""  # ← 这就是 description
    ...
```

SDK 会：

1. 读取函数的 docstring
2. 作为工具的 `description` 字段
3. 注册到 Agent 的 `tools` 里
4. 发给模型时包含在 function schema 中

模型根据这个 `description` 决定什么时候该调用这个工具。

### 自定义 FunctionTool

如果不想用 Python 函数作为工具，可以直接创建 `FunctionTool`：

```python
from agents import FunctionTool, RunContextWrapper
from pydantic import BaseModel

class AnalyzeArgs(BaseModel):
    project_id: str
    date_range: str

async def run_custom_analyze(ctx: RunContextWrapper, args: str) -> str:
    parsed = AnalyzeArgs.model_validate_json(args)
    return f"[custom_analyze] 项目 {parsed.project_id} 在 {parsed.date_range} 的分析完成"

custom_tool = FunctionTool(
    name="custom_analyze",
    description="自定义分析工具：深度分析项目数据",
    params_json_schema=AnalyzeArgs.model_json_schema(),
    on_invoke_tool=run_custom_analyze,
)
```

适合：

```text
需要完全手动控制工具定义和执行
需要自定义参数校验逻辑
需要访问 RunContextWrapper
```

---

## 3. ShellTool (本地 shell 执行)

**重要**：`ShellTool` / `Shell()` 能力必须在 sandbox 环境里运行。

```python
from agents import SandboxAgent, Runner, RunConfig
from agents.sandbox import SandboxRunConfig
from agents.sandbox.capabilities import Shell
from agents.sandbox.sandboxes.unix_local import UnixLocalSandboxClient

agent = SandboxAgent(  # 必须是 SandboxAgent
    capabilities=[Shell()],
    ...
)

result = await Runner.run(
    agent,
    prompt,
    run_config=RunConfig(
        sandbox=SandboxRunConfig(client=UnixLocalSandboxClient())
    ),
)
```

### 为什么必须用 sandbox？

因为：

```text
Shell 命令执行需要隔离环境
需要 workspace 管理
需要安全边界
```

### 不想用 sandbox 怎么办？

用 `@function_tool` 自己包装：

```python
@function_tool
def run_local_command(cmd: str) -> str:
    import subprocess
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout
```

但安全性你要自己控制：

```text
限制命令白名单
限制工作目录
限制文件大小
限制运行时间
限制并发 run
```

---

## 4. 工具返回图像或文件

### 返回图像

```python
from agents import function_tool
from agents.tool import ToolOutputImage

@function_tool
def get_material_thumbnail(material_id: str) -> ToolOutputImage:
    """获取素材缩略图。"""
    red_png_base64 = "iVBORw0KGgo..."
    return ToolOutputImage(
        image_url=f"data:image/png;base64,{red_png_base64}",
        detail="low",  # 'low', 'high', 'auto'
    )
```

**关键字段**：

```python
ToolOutputImage:
  image_url  # data URL 或 URL
  file_id    # 已上传文件 ID
  detail     # 图像分辨率
```

**注意**：

```text
不是 data= 字段
不是 mime_type= 字段
必须是 image_url 或 file_id
```

### 返回文件

```python
import base64
from agents.tool import ToolOutputFileContent

@function_tool
def download_campaign_report(project_id: str) -> ToolOutputFileContent:
    """下载投放报告文件。"""
    report_content = f"# {project_id} 投放报告\n\n- CTR: 2.5%\n- ROI: 3.2\n"
    report_base64 = base64.b64encode(report_content.encode("utf-8")).decode("utf-8")
    return ToolOutputFileContent(
        filename=f"{project_id}_report.md",
        file_data=f"data:text/plain;base64,{report_base64}",
    )
```

**关键字段**：

```python
ToolOutputFileContent:
  file_data   # data URL 格式 base64
  file_url    # 文件 URL
  file_id     # 已上传文件 ID
  filename    # 文件名（可选）
```

**注意**：

```text
不是 content= 字段
不是 name= 字段
file_data 必须是 data URL 格式，不是裸 base64
例如：data:text/plain;base64,IyBQ...
```

### 适合场景

对 ANIFORCE 来说：

```text
返回图像：
  - 素材缩略图
  - 广告预览图
  - 数据可视化图表

返回文件：
  - 投放报告
  - 素材包清单
  - 分析结果 Excel
  - 配置文件
```

---

## 5. 函数工具超时

### 基本用法

```python
@function_tool(timeout=1.0, timeout_behavior="error_as_result")
async def slow_material_metrics(material_id: str) -> str:
    """查询素材指标。超时后把错误作为工具结果返回给模型。"""
    await asyncio.sleep(3)
    return f"素材 {material_id}: CTR=2.3%, ROI=3.5"
```

### timeout_behavior 两种模式

#### 1. error_as_result（默认）

```python
timeout_behavior="error_as_result"
```

工具超时后：

```text
超时信息变成工具输出
例如："Tool 'slow_material_metrics' timed out after 1 seconds."
模型看到这个输出
模型可以继续给用户解释"查询超时"
Runner.run 不崩溃
```

适合：

```text
查询辅助信息
获取补充数据
拉取外部趋势
读取可选素材
非关键操作
```

好处：

```text
Agent 可以恢复
用户体验更顺滑
```

#### 2. raise_exception

```python
timeout_behavior="raise_exception"
```

工具超时后：

```text
直接抛 ToolTimeoutError
Runner.run 失败
业务层捕获异常
```

适合：

```text
创建 campaign
发布广告
扣费/预算修改
写入数据库
上传正式素材
关键操作
```

好处：

```text
不会让模型在关键操作失败后继续假装成功
系统可以明确回滚或提示失败
```

### 为什么主要对异步工具生效？

因为超时本质上依赖：

```python
await asyncio.wait_for(...)
```

异步函数是可中断的：

```python
async def tool():
    await asyncio.sleep(10)  # 可以被取消
```

同步函数不一样：

```python
def slow_tool():
    time.sleep(10)  # 当前线程被卡住，不能安全中断
```

所以：

```text
async 工具：可以用 asyncio timeout 取消
sync 工具：不能可靠安全地中断
```

如果同步工具也需要超时，推荐：

```text
1. 改成 async 工具
2. 工具内部自己设置超时，比如 httpx timeout、requests timeout
3. 放到 subprocess / worker / queue 中执行，由外层杀进程或取消任务
```

### ANIFORCE 推荐超时策略

```python
轻量查询工具：2-5 秒
  @function_tool(timeout=3.0)

第三方平台查询：10-30 秒
  @function_tool(timeout=20.0)

素材分析/报告生成：30-120 秒
  @function_tool(timeout=60.0, timeout_behavior="error_as_result")

高风险写操作：超时直接失败
  @function_tool(timeout=10.0, timeout_behavior="raise_exception")
```

---

## 6. 函数工具错误处理

### 三种错误处理模式

#### 1. 默认错误处理

```python
@function_tool  # 不传 failure_error_function
def flaky_meta_query(campaign_id: str) -> str:
    if campaign_id == "C001":
        return "广告系列 C001: 花费 $5000, ROI 2.8"
    raise ValueError(f"Meta API 返回错误: campaign_id={campaign_id} 不存在")
```

行为：

```text
工具抛异常后，SDK 运行 default_tool_error_function
返回通用错误消息给模型
例如："An error occurred while running the tool. Please try again."
模型可以继续给用户建议
Runner.run 不崩溃
```

#### 2. 自定义错误函数

```python
from agents import RunContextWrapper
from typing import Any

def custom_error_handler(context: RunContextWrapper[Any], error: Exception) -> str:
    """自定义错误处理：记录日志，返回用户友好提示。"""
    print(f"[ERROR_LOG] 工具调用失败: {error}")
    return "内部服务暂时不可用，请稍后重试或联系技术支持。"

@function_tool(failure_error_function=custom_error_handler)
def flaky_material_upload(material_id: str) -> str:
    if material_id == "M001":
        return f"素材 {material_id} 上传成功"
    raise RuntimeError(f"OSS 上传失败: 素材 {material_id} 格式错误")
```

好处：

```text
记录完整错误日志供排查
隐藏内部错误细节
给模型返回用户友好提示
可以区分错误类型
可以返回结构化错误信息
```

#### 3. None：错误直接抛出

```python
@function_tool(failure_error_function=None)
def critical_publish_ad(ad_id: str) -> str:
    """发布广告（关键操作）。失败后直接抛异常。"""
    if ad_id == "AD001":
        return f"广告 {ad_id} 发布成功"
    raise PermissionError(f"权限不足：无法发布广告 {ad_id}")
```

行为：

```text
工具抛异常后，直接向上抛
Runner.run 失败
业务层必须 try/except 捕获
```

适合：

```text
权限相关
付费/扣款/预算操作
数据一致性操作
状态不对时不能继续
必须回滚或中止
```

**问题**：对话会直接挂掉，用户体验不好。

---

### 更友好的方式：结构化错误处理

```python
import json

def structured_error_handler(ctx: RunContextWrapper, error: Exception) -> str:
    log_error(error, ctx)  # 内部记录完整错误
    
    if isinstance(error, PermissionError):
        return json.dumps({
            "success": False,
            "error_code": "PERMISSION_DENIED",
            "message": "权限不足，请联系管理员开通权限",
            "retryable": False
        })
    elif isinstance(error, InsufficientFundsError):
        return json.dumps({
            "success": False,
            "error_code": "INSUFFICIENT_FUNDS",
            "message": f"余额不足，当前余额: {get_balance()}",
            "retryable": False
        })
    else:
        return json.dumps({
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message": "操作失败，请稍后重试",
            "retryable": True
        })

@function_tool(failure_error_function=structured_error_handler)
def create_campaign(...):
    if not has_permission(...):
        raise PermissionError(...)
    ...
```

**好处**：

```text
对话不会挂
模型能看到结构化错误
模型可以给用户明确建议
Backend 可以记录完整错误
前端可以解析 error_code 展示不同 UI
```

---

### 生产必须考虑的场景

#### 1. 权限相关

```python
@function_tool(failure_error_function=structured_error_handler)
def create_campaign(...):
    if not has_permission(user_id, "create_campaign"):
        raise PermissionError("用户无权限创建广告系列")
```

**为什么要处理而不是直接抛？**

```text
权限错误不能让模型继续编答案
但也不应该让对话直接挂掉
应该返回结构化错误
前端显示权限申请入口
记录审计日志
```

#### 2. 付费/扣款/预算操作

```python
@function_tool(failure_error_function=structured_error_handler)
def charge_budget(amount: float):
    if balance < amount:
        raise InsufficientFundsError("余额不足")
```

**为什么要处理？**

```text
扣款失败不能让模型说"已扣款成功"
必须让前端明确提示余额不足
不能让用户误以为操作成功
但可以让对话继续，模型建议用户充值
```

#### 3. 敏感信息泄露防护

```python
def safe_error_handler(ctx, error: Exception) -> str:
    # 记录完整错误（含敏感信息）
    log_to_internal_system(error)
    
    # 返回给模型（脱敏）
    return "操作失败，请联系技术支持"
```

**为什么要自定义？**

```text
原始错误可能包含：
- 数据库连接串
- 内部 IP
- 用户真实数据
- API key

模型看到错误后会在回答里暴露给用户
所以必须脱敏
```

#### 4. 审计和告警

```python
def audit_and_alert_error_handler(ctx, error: Exception) -> str:
    # 记录到审计日志
    audit_log.error(
        user_id=ctx.get("user_id"),
        tool="publish_campaign",
        error=str(error),
        timestamp=now()
    )
    
    # 关键错误发告警
    if isinstance(error, CriticalError):
        send_alert_to_ops(error)
    
    return "发布失败，技术团队已收到告警"
```

**生产价值**：

```text
知道哪些工具经常失败
知道哪些用户遇到问题
可以做错误统计和优化
关键错误及时响应
```

#### 5. 错误分类和前端展示

```python
def categorized_error_handler(ctx, error: Exception) -> str:
    if isinstance(error, PermissionError):
        return "[PERMISSION_ERROR] 权限不足，请联系管理员"
    elif isinstance(error, ValidationError):
        return "[VALIDATION_ERROR] 数据格式错误，请检查输入"
    elif isinstance(error, TimeoutError):
        return "[TIMEOUT_ERROR] 请求超时，请稍后重试"
    else:
        return "[INTERNAL_ERROR] 内部错误，请联系技术支持"
```

**前端可以根据错误类型展示不同 UI**：

```text
PERMISSION_ERROR -> 显示权限申请入口
VALIDATION_ERROR -> 高亮错误字段
TIMEOUT_ERROR -> 显示重试按钮
INTERNAL_ERROR -> 显示工单入口
```

---

### ANIFORCE 推荐策略

```python
# 查询类：自定义友好提示
@function_tool(failure_error_function=log_and_friendly_message)
def query_campaign_metrics(...):
    ...

# 写入类（非关键）：结构化错误处理
@function_tool(failure_error_function=structured_error_handler)
def create_campaign(...):
    ...

@function_tool(failure_error_function=structured_error_handler)
def publish_to_meta(...):
    ...

# 第三方 API：记录日志 + 分类错误
@function_tool(failure_error_function=categorized_platform_error_handler)
def sync_meta_ads(...):
    ...

# 素材处理：可恢复
@function_tool(failure_error_function=lambda ctx, e: "素材处理失败，请检查格式")
def analyze_material(...):
    ...
```

### 推荐：Backend 侧先做校验

更友好的方式是在 Backend API 层先做校验：

```python
# Backend API 层
@router.post("/campaigns/create")
async def create_campaign_api(payload, user=Depends(get_current_user)):
    # 先校验权限
    if not has_permission(user.id, "create_campaign"):
        raise HTTPException(
            status_code=403,
            detail={"code": "PERMISSION_DENIED", "message": "权限不足"}
        )
    
    # 校验余额
    if user.balance < payload.budget:
        raise HTTPException(
            status_code=400,
            detail={"code": "INSUFFICIENT_FUNDS", "message": "余额不足"}
        )
    
    # 校验通过后再调 MCP tool
    return await mcp_tool.create_campaign(...)
```

**Agent 工具只处理已校验的请求**：

```python
@function_tool  # 不会遇到权限/余额错误
async def create_campaign_validated(campaign_data: dict) -> str:
    # Backend 已经校验过，这里只做创建
    result = await backend_api.create_campaign(campaign_data)
    return json.dumps(result)
```

**混合策略**：

```text
权限错误 → Backend 拦截 → 前端显示权限申请入口 → 对话不启动
余额不足 → Backend 拦截 → 前端显示充值入口 → 对话不启动
业务异常 → Agent 工具返回结构化错误 → 模型给建议 → 对话继续
```

这样比直接抛异常或完全依赖 Agent 工具错误处理更友好、更可控。

---

## 总结

这些工具运行时能力对 ANIFORCE 生产环境的价值：

```text
1. ModelSettings 高级参数：控制并发、缓存、压缩策略
2. 本地函数工具：封装业务逻辑，清晰 schema
3. 工具返回图像/文件：支持素材预览、报告下载
4. 工具超时：防止被慢工具卡死，区分可恢复/不可恢复
5. 错误处理：友好提示 + 日志审计 + 前端体验 + 安全脱敏
```

生产部署时，工具超时和错误处理是最关键的两个环节，直接影响系统稳定性和用户体验。

---

## 7. 安全防护措施 (Guardrails)

**当前状态：先忽略，待后续有时间再深入调试。**

### 核心概念

安全防护措施使你能够对用户输入和智能体输出进行检查和验证。

三种防护类型：

```text
输入安全防护（Input Guardrails）：
  在初始用户输入上运行，第一个 Agent 运行前检查
  
输出安全防护（Output Guardrails）：
  在最终 Agent 输出上运行，返回给用户前检查
  
工具安全防护（Tool Guardrails）：
  在每次函数工具调用时运行
  输入防护在工具执行前，输出防护在工具执行后
```

### 典型应用场景

对 ANIFORCE 来说：

#### 输入防护

```text
检查用户是否在问无关问题（比如问数学题、写论文）
检查是否尝试注入 prompt
检查是否包含敏感词/违规内容
检查用户权限（比如免费用户不能问高级功能）
检查输入是否包含恶意代码/SQL注入
```

好处：

```text
阻止恶意请求，不浪费昂贵的模型 token
避免 Agent 被滥用
保护系统安全
节省成本
```

#### 输出防护

```text
检查 Agent 回答是否泄露敏感信息（API key、内部配置）
检查回答是否包含不当内容
检查回答是否符合业务规范
检查是否违反广告平台政策
```

好处：

```text
防止 Agent 输出敏感信息
确保输出合规
保护用户隐私
```

#### 工具防护

```text
检查工具调用参数是否包含敏感信息
检查工具返回是否泄露数据
阻止危险操作
```

### 执行模式

输入防护支持两种执行模式：

```python
# 并行执行（默认）
run_in_parallel=True
  防护和 Agent 并发运行
  延迟最优
  但防护失败时 Agent 可能已经消耗 token

# 阻塞执行
run_in_parallel=False
  防护先运行并完成
  防护触发时 Agent 不会执行
  避免 token 消耗和工具副作用
  适合成本优化
```

### 为什么现在先忽略？

```text
短期 MVP：
  - 用户是内部或受信任的
  - 可以先依赖 Backend 权限控制
  - 可以先手动审查输出

中长期生产：
  - 必须防止恶意输入
  - 必须保护敏感信息不泄露
  - 必须确保合规
  - 必须节省成本
```

### 推荐接入优先级

```text
1. Backend API 层权限校验（现在就做）
2. 输入防护：检查恶意输入、越权操作（中期必须）
3. 输出防护：检查敏感信息泄露（中期必须）
4. 工具防护：检查工具调用安全（长期）
```

### 结论

安全防护措施对生产有实际意义，但不是第一优先级。当前阶段先依赖 Backend 权限控制，等权限、错误处理、超时这些核心功能稳定后再接入完整的 Guardrails 体系。
