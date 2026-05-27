"""手动重命名 organizations 表的 org_id 字段为 org_code"""
import sqlite3
import sys
from pathlib import Path

# 数据库路径
DB_PATH = Path(__file__).parent.parent / "data" / "aniforce.db"

def rename_org_id_to_org_code():
    """重命名 org_id 为 org_code"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 检查当前表结构
        cursor.execute("PRAGMA table_info(organizations)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print(f"当前字段: {column_names}")
        
        # 检查是否已经有 org_code 字段
        if 'org_code' in column_names:
            print("✓ org_code 字段已存在，无需重命名")
            conn.close()
            return True
        
        # 检查是否有 org_id 字段
        if 'org_id' not in column_names:
            print("✗ org_id 字段不存在，无法重命名")
            conn.close()
            return False
        
        print("开始重命名 org_id -> org_code...")
        
        # SQLite 重命名列需要重建表
        # 1. 创建新表
        cursor.execute("""
            CREATE TABLE organizations_new (
                id VARCHAR(36) NOT NULL,
                name VARCHAR(255) NOT NULL,
                org_code VARCHAR(100) NOT NULL,
                description TEXT,
                invite_code VARCHAR(100),
                owner_id VARCHAR(36) NOT NULL,
                status VARCHAR(20) DEFAULT 'active' NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                PRIMARY KEY (id),
                FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE (org_code)
            )
        """)
        
        # 2. 复制数据
        cursor.execute("""
            INSERT INTO organizations_new 
            (id, name, org_code, description, invite_code, owner_id, status, created_at, updated_at)
            SELECT id, name, org_id, description, invite_code, owner_id, status, created_at, updated_at
            FROM organizations
        """)
        
        # 3. 删除旧表
        cursor.execute("DROP TABLE organizations")
        
        # 4. 重命名新表
        cursor.execute("ALTER TABLE organizations_new RENAME TO organizations")
        
        # 5. 重建索引
        cursor.execute("CREATE INDEX ix_organizations_org_code ON organizations (org_code)")
        cursor.execute("CREATE INDEX ix_organizations_owner_id ON organizations (owner_id)")
        cursor.execute("CREATE INDEX ix_organizations_status ON organizations (status)")
        
        # 6. 为 invite_code 添加约束和索引（如果需要）
        if 'invite_code' in column_names:
            # 为 NULL 的 invite_code 生成值
            cursor.execute("UPDATE organizations SET invite_code = 'invite_' || org_code WHERE invite_code IS NULL")
            # 注意：SQLite 不支持直接添加 NOT NULL 约束到现有列
            # 需要在重建表时就设置好
        
        conn.commit()
        print("✓ 重命名成功！")
        
        # 验证
        cursor.execute("PRAGMA table_info(organizations)")
        new_columns = cursor.fetchall()
        new_column_names = [col[1] for col in new_columns]
        print(f"新字段: {new_column_names}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ 错误: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    success = rename_org_id_to_org_code()
    sys.exit(0 if success else 1)
