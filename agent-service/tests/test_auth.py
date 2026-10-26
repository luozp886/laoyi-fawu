"""用户认证与安全模块测试：密码哈希、双 token 签发/校验、白名单与鉴权依赖。

不依赖数据库：仅验证密码哈希往返、JWT 令牌、刷新令牌哈希与
get_current_user_id 依赖的三步校验（白名单放行 / 缺 token 401 / 无效 token 401）。
"""
import jwt
import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.config import settings
from app.modules.user.service import password_hash
from app.security import (
    WHITELIST_PATHS,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    get_current_user_id,
    hash_refresh_token,
    is_whitelisted,
)


def test_password_hash_roundtrip():
    """argon2 哈希可校验、错误密码被拒绝。"""
    hashed = password_hash.hash("123456")
    assert hashed != "123456"
    assert password_hash.verify("123456", hashed)
    assert not password_hash.verify("654321", hashed)


def test_access_token_contains_user_id_and_type():
    """访问令牌能解析出用户 id 与 type=access。"""
    token = create_access_token(user_id=42)
    payload = jwt.decode(token, settings.app.jwt_secret, algorithms=["HS256"])
    assert payload["sub"] == "42"
    assert payload["type"] == "access"
    assert decode_access_token(token) == 42


def test_invalid_access_token_rejected():
    """无效/伪造令牌被拒绝并返回 401。"""
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token("not-a-jwt")
    assert exc_info.value.status_code == 401

    # 用刷新令牌类型的 payload 冒充访问令牌也应被拒绝
    from datetime import datetime, timedelta, timezone
    forged = jwt.encode(
        {"sub": "1", "type": "refresh", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        settings.app.jwt_secret,
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(forged)
    assert exc_info.value.status_code == 401


def test_refresh_token_opaque_and_hashed():
    """刷新令牌为随机不透明串，数据库只保存 SHA-256 哈希。"""
    token = create_refresh_token()
    assert len(token) >= 32
    hashed = hash_refresh_token(token)
    assert hashed != token
    assert hashed == hash_refresh_token(token)
    assert len(hashed) == 64


def test_whitelist_paths():
    """白名单路径放行，其余路径需要鉴权。"""
    assert is_whitelisted("/health")
    assert is_whitelisted("/api/v1/auth/login")
    assert is_whitelisted("/api/v1/auth/refresh")
    assert not is_whitelisted("/api/v1/chat")
    assert not is_whitelisted("/api/v1/chat-threads")
    assert "/api/v1/auth/login" in WHITELIST_PATHS


def test_get_current_user_id_dependency():
    """鉴权依赖三步校验：缺 token → 401；带有效 token → 返回用户 id。"""
    app = FastAPI()

    @app.get("/protected")
    def protected(user_id: int = Depends(get_current_user_id)):
        return {"user_id": user_id}

    client = TestClient(app)

    # 1. 无 Authorization 头 → 401
    response = client.get("/protected")
    assert response.status_code == 401

    # 2. 非 Bearer 格式 → 401
    response = client.get("/protected", headers={"Authorization": "Token abc"})
    assert response.status_code == 401

    # 3. 无效 token → 401
    response = client.get("/protected", headers={"Authorization": "Bearer invalid.jwt.token"})
    assert response.status_code == 401

    # 4. 有效 token → 放行并返回用户 id
    token = create_access_token(user_id=7)
    response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == {"user_id": 7}
