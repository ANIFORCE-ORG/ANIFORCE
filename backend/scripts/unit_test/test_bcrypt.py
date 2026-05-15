"""测试 bcrypt 密码加密"""
import sys
from pathlib import Path

# 添加 backend 目录到 Python 路径
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 测试不同长度的密码
test_passwords = [
    "abc123",
    "test123",
    "password123",
    "a" * 50,
    "a" * 72,
]

print("=" * 60)
print("测试 bcrypt 密码加密")
print("=" * 60)

for password in test_passwords:
    print(f"\n密码: '{password}' (长度: {len(password)}, 字节: {len(password.encode('utf-8'))})")
    try:
        hash_result = pwd_context.hash(password)
        print(f"✅ 加密成功")
        print(f"   哈希: {hash_result[:50]}...")
        
        # 验证
        is_valid = pwd_context.verify(password, hash_result)
        print(f"   验证: {'✅ 成功' if is_valid else '❌ 失败'}")
    except Exception as e:
        print(f"❌ 加密失败: {e}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
