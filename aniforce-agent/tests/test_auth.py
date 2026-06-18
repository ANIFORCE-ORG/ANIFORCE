"""JWT 认证测试"""
import pytest
from app.core.auth import create_access_token, decode_access_token, AuthError


def test_create_and_decode_token():
    """测试 Token 创建和解析"""
    data = {"sub": "user123", "email": "test@example.com", "name": "Test User"}
    token = create_access_token(data)
    
    assert token is not None
    assert isinstance(token, str)
    
    payload = decode_access_token(token)
    assert payload["sub"] == "user123"
    assert payload["email"] == "test@example.com"
    assert payload["name"] == "Test User"


def test_decode_invalid_token():
    """测试解析无效 Token"""
    with pytest.raises(AuthError):
        decode_access_token("invalid.token.here")


def test_decode_expired_token():
    """测试解析过期 Token"""
    from datetime import timedelta
    
    data = {"sub": "user123"}
    token = create_access_token(data, expires_delta=timedelta(seconds=-1))
    
    with pytest.raises(AuthError):
        decode_access_token(token)
