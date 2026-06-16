from __future__ import annotations

import argparse
import json
from dataclasses import fields, is_dataclass
from typing import Any, get_args

from loguru import logger

import claude_agent_sdk as sdk
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ContentBlock,
    ResultMessage,
    ServerToolResultBlock,
    ServerToolUseBlock,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

from sdk_learning_common import OUT_DIR, setup_logger

# 第 3 章主题：Python Reference。
# 单一职责：对 SDK 真实类型做静态自省，确认 API/类型/options 的真身。
# 不调用模型，避免消耗 token 和中转 403 干扰；纯 import + dataclass 反射。

MESSAGE_TYPES = [UserMessage, AssistantMessage, SystemMessage, ResultMessage]
BLOCK_TYPES = [
    TextBlock,
    ThinkingBlock,
    ToolUseBlock,
    ToolResultBlock,
    ServerToolUseBlock,
    ServerToolResultBlock,
]


def describe_dataclass(cls: type) -> dict[str, Any]:
    """把一个 dataclass 的字段抽成 {名字, 类型, 是否必填} 列表。"""
    if not is_dataclass(cls):
        return {"name": cls.__name__, "is_dataclass": False}
    from dataclasses import MISSING

    field_rows = []
    for f in fields(cls):
        # dataclass 字段：default 或 default_factory 任一存在即为可选
        optional = not (f.default is MISSING and f.default_factory is MISSING)
        field_rows.append(
            {
                "field": f.name,
                "type": _type_name(f.type),
                "required": not optional,
            }
        )
    return {"name": cls.__name__, "is_dataclass": True, "fields": field_rows}


def _type_name(tp: Any) -> str:
    if isinstance(tp, str):
        return tp
    return getattr(tp, "__name__", str(tp)).replace("typing.", "")


def describe_union(name: str, union_type: Any) -> dict[str, Any]:
    return {"name": name, "members": [_type_name(a) for a in get_args(union_type)]}


def run() -> dict[str, Any]:
    setup_logger("03_python_reference")
    logger.info("开始第 3 章 Python Reference 静态自省 (不调用模型)")
    logger.info("SDK 版本: {}", sdk.__version__)

    # 1. 消息类型
    messages = [describe_dataclass(cls) for cls in MESSAGE_TYPES]
    for m in messages:
        required = [f["field"] for f in m["fields"] if f["required"]]
        logger.info("Message {}: 必填字段={}", m["name"], required)

    # 2. content block 类型 + ContentBlock 联合
    blocks = [describe_dataclass(cls) for cls in BLOCK_TYPES]
    for b in blocks:
        logger.info(
            "Block {}: 字段={}", b["name"], [f["field"] for f in b["fields"]]
        )
    content_union = describe_union("ContentBlock", ContentBlock)
    logger.info("ContentBlock 联合成员: {}", content_union["members"])

    # 3. ClaudeAgentOptions 全字段
    options = describe_dataclass(ClaudeAgentOptions)
    opt_required = [f["field"] for f in options["fields"] if f["required"]]
    logger.info(
        "ClaudeAgentOptions: 共 {} 个字段, 必填={}",
        len(options["fields"]),
        opt_required or "无 (全部有默认值)",
    )

    # 4. 关键 Literal 取值
    permission_modes = list(get_args(sdk.PermissionMode))
    effort_levels = list(get_args(sdk.EffortLevel))
    logger.info("PermissionMode 取值: {}", permission_modes)
    logger.info("EffortLevel 取值: {}", effort_levels)

    # 5. 公开 API 面 (__all__)
    public_api = sorted(sdk.__all__)
    logger.info("公开 API 数量: {}", len(public_api))

    summary = {
        "sdk_version": sdk.__version__,
        "messages": messages,
        "blocks": blocks,
        "content_block_union": content_union,
        "options": options,
        "permission_modes": permission_modes,
        "effort_levels": effort_levels,
        "public_api_count": len(public_api),
        "public_api": public_api,
    }
    summary_path = OUT_DIR / "03_python_reference_summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    logger.info("第 3 章自省摘要已写出: {}", summary_path)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Chapter 3: Python Reference introspection.")
    return parser.parse_args()


def main() -> None:
    parse_args()
    run()


if __name__ == "__main__":
    main()

