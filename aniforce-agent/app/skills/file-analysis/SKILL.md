---
name: file-analysis
description: "分析文件内容并生成摘要报告"
---

# File Analysis Skill

## 目标

读取指定文件，分析内容特征，生成结构化摘要报告。

## 输入

- `file_path`: 要分析的文件路径（相对于当前工作目录）

## 输出

生成报告文件 `analysis_report.txt`，包含：
- 文件大小
- 行数
- 字符数
- 关键词统计

## 工作流

1. 使用 `Read` 工具读取文件内容
2. 分析文件特征（行数、字符数、常见词）
3. 使用 `Write` 工具写入报告到 `analysis_report.txt`
4. 返回报告路径

## 示例

用户输入：
```
请分析文件 test.txt
```

Agent 执行：
1. `Read(path="test.txt")`
2. 分析内容
3. `Write(path="analysis_report.txt", content="...")`
4. 回复："已完成分析，报告已保存到 analysis_report.txt"

## 硬约束

- 只能读取当前 Sandbox 内的文件
- 报告必须保存为 `analysis_report.txt`
- 如果文件不存在，返回明确错误信息
