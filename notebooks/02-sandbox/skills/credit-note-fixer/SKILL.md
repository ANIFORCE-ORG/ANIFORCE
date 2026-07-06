---
name: credit-note-fixer
description: 修复 credit-note 格式化 bug，并重新运行指定测试命令。
---

# Credit Note Fixer

按下面流程执行：

1. 读取 `repo/task.md`。
2. 检查 `repo/credit_note.sh` 和 `repo/tests/test_credit_note.sh`。
3. 做最小正确修改：输出标签必须是 `credit`，金额必须始终显示为正数。
   如果使用 `apply_patch`，路径使用相对于沙盒工作区根目录的路径，例如 `repo/credit_note.sh`。
4. 在 `repo/` 目录下运行：`sh tests/test_credit_note.sh`。
5. 最终回答中说明 bug、修复内容，以及实际运行的验证命令。
