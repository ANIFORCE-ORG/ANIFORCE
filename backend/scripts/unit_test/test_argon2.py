"""测试 argon2 密码加密"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from passlib.context import CryptContext

# 使用 argon2
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

test_passwords = ["test123", "123456", "password123", "a" * 50]

print("=" * 60)
print("测试 argon2 密码加密")
print("=" * 60)

for password in test_passwords:
    print(f"\n密码: '{password}' (长度: {len(password)})")
    try:
        hash_result = pwd_context.hash(password)
        print(f"✅ 加密成功")
        print(f"   哈希: {hash_result[:60]}...")
        
        is_valid = pwd_context.verify(password, hash_result)
        print(f"   验证: {'✅ 成功' if is_valid else '❌ 失败'}")
    except Exception as e:
        print(f"❌ 加密失败: {e}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
