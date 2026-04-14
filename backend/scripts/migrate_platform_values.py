"""迁移脚本：更新campaign表的platform字段值"""
import asyncio
import sqlite3
from pathlib import Path

# 数据库路径
DB_PATH = Path(__file__).parent.parent / "data" / "sqlite" / "animagus.db"

# 平台值映射
PLATFORM_MAPPING = {
    "google": "Google",
    "tiktok": "TikTok",
    "meta": "Meta",
    # 兼容已经是新值的情况
    "Google": "Google",
    "TikTok": "TikTok",
    "Meta": "Meta",
}


def migrate_platform_values():
    """更新platform字段值"""
    print(f"连接数据库: {DB_PATH}")
    
    if not DB_PATH.exists():
        print(f"数据库文件不存在: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 查询所有campaign记录
        cursor.execute("SELECT id, platform FROM campaigns")
        campaigns = cursor.fetchall()
        
        print(f"找到 {len(campaigns)} 条campaign记录")
        
        updated_count = 0
        for campaign_id, old_platform in campaigns:
            # 获取新的platform值
            new_platform = PLATFORM_MAPPING.get(old_platform)
            
            if new_platform and new_platform != old_platform:
                print(f"更新 campaign {campaign_id}: {old_platform} -> {new_platform}")
                cursor.execute(
                    "UPDATE campaigns SET platform = ? WHERE id = ?",
                    (new_platform, campaign_id)
                )
                updated_count += 1
            elif not new_platform:
                print(f"警告: campaign {campaign_id} 的platform值 '{old_platform}' 不在映射表中")
        
        # 提交更改
        conn.commit()
        print(f"\n成功更新 {updated_count} 条记录")
        
        # 验证更新结果
        cursor.execute("SELECT DISTINCT platform FROM campaigns")
        platforms = cursor.fetchall()
        print(f"\n当前数据库中的platform值: {[p[0] for p in platforms]}")
        
    except Exception as e:
        print(f"迁移失败: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    migrate_platform_values()
