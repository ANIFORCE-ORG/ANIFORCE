"""Typed business decision contracts for the Workspace Agent."""

from dataclasses import dataclass


@dataclass(frozen=True)
class BusinessSkill:
    name: str
    version: str
    description: str
    trigger_examples: tuple[str, ...]
    required_slots: tuple[str, ...]
    clarification_rules: tuple[str, ...]
    evidence_contract: tuple[str, ...]
    workflow: tuple[str, ...]
    allowed_tools: frozenset[str]
    response_contract: tuple[str, ...]
    write_verification: tuple[str, ...] = ()

    def render_contract(self) -> str:
        def section(title: str, values: tuple[str, ...]) -> list[str]:
            return [f"## {title}", *(f"- {value}" for value in values)]

        lines = [
            f"# Business Skill: {self.name}",
            f"- 版本：{self.version}",
            f"- 用途：{self.description}",
            f"- 必要槽位：{', '.join(self.required_slots) or '无'}",
        ]
        lines += section("澄清规则", self.clarification_rules)
        lines += section("证据合同", self.evidence_contract)
        lines += section("执行流程", self.workflow)
        lines += section("回答合同", self.response_contract)
        if self.write_verification:
            lines += section("写后验证", self.write_verification)
        return "\n".join(lines)
