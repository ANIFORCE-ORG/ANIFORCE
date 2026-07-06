# 任务

`credit_note.sh` 当前格式化 credit note 的结果是错的：

- 它输出了 `debit`，但正确标签应该是 `credit`。
- 它保留了负号，但 credit note 的金额应该始终显示为正数。

请做最小正确修改，然后在 `repo/` 目录下运行这个验证命令：

`sh tests/test_credit_note.sh`

如果你使用 `apply_patch`，补丁路径必须相对于沙盒工作区根目录。
也就是说，文件路径应写成 `repo/credit_note.sh`，而不是只写 `credit_note.sh`。

不要修改测试期望。
