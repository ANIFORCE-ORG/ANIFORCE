# Scripts 目录说明

本目录用于维护所有后端相关的脚本文件。

## 目录结构

```
scripts/
├── data_migrate/     # 数据迁移相关脚本
├── data_mock/        # 数据 mocking 测试的创建脚本
├── unit_test/        # 临时测试脚本
└── README.md         # 本说明文件
```

## 各目录用途

### 📦 data_migrate/
用于存放数据迁移脚本，包括：
- 数据库结构迁移
- 数据格式转换
- 历史数据导入/导出
- 数据库版本升级脚本

**示例**：
- `migrate_platform_values.py` - 平台字段值迁移

### 🎭 data_mock/
用于存放数据 mocking 和测试数据创建脚本，包括：
- 生成测试数据
- 创建 mock 用户
- 填充示例数据
- 性能测试数据准备

**示例**：
- `seed_mock_data.py` - 填充 mock 数据

### 🧪 unit_test/
用于存放临时测试脚本，包括：
- 功能验证脚本
- API 测试脚本
- 数据库操作测试
- 集成测试脚本

**示例**：
- `test_db_write.py` - 数据库写入测试
- `test_db_query.py` - 数据库查询测试

## 使用规范

1. **命名规范**
   - 使用小写字母和下划线
   - 文件名应清晰描述脚本用途
   - 例如：`migrate_user_table.py`, `seed_campaign_data.py`, `test_auth_api.py`

2. **文档要求**
   - 每个脚本应包含文档字符串说明用途
   - 复杂脚本应包含使用示例
   - 注明依赖的环境变量或配置

3. **执行方式**
   ```bash
   # 从 backend 目录执行
   cd backend
   python scripts/unit_test/test_db_write.py
   ```

4. **注意事项**
   - 迁移脚本执行前应备份数据
   - Mock 脚本不应在生产环境执行
   - 测试脚本应可重复执行
