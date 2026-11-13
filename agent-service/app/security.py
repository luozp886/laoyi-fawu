"""统一安全校验模块：JWT 访问令牌签发/校验 + 刷新令牌工具 + 路由鉴权依赖。

三大校验步骤（供 FastAPI 依赖注入使用，见 get_current_user_id）：
1. 是否为白名单请求路径 —— 是则直接放行；
2. 请求头 Authorization: Bearer <token> 是否存在 —— 不存在返回 401；
3. 校验 token 是否有效 —— 无效/过期返回 401。
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError

from app.core.config import settings

# 无需登录即可访问的白名单路径（精确匹配，忽略末尾斜杠）
WHITELIST_PATHS: frozenset[str] = frozenset(
    {
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/refresh",
        "/api/v1/auth/logout",
    }
)

# Bearer 令牌方案：用于 OpenAPI/Swagger 的 Authorize 按钮
bearer_scheme = HTTPBearer(
    auto_error=False,
    description="登录/注册/刷新接口返回的访问令牌（access token），格式：Bearer <token>",
)


def is_whitelisted(path: str) -> bool:
    """判断请求路径是否命中白名单。"""
    normalized = path.rstrip("/") or "/"
    return normalized in WHITELIST_PATHS


def create_access_token(user_id: int) -> str:
    """签发短时有效的访问令牌（JWT, HS256）。

    双 token 机制中的 access token：有效期短（默认 120 分钟），
    过期后由前端携带 refresh token 调用 /auth/refresh 自动续期。
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.app.jwt_access_expire_minutes),
    }
    return jwt.encode(payload, settings.app.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> int:
    """校验访问令牌并返回用户 ID；无效/过期抛出 401。"""
    try:
        payload = jwt.decode(token, settings.app.jwt_secret, algorithms=["HS256"])
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录已失效，请重新登录",
        ) from exc

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录已失效，请重新登录",
        )

    try:
        return int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录已失效，请重新登录",
        ) from exc


def create_refresh_token() -> str:
    """生成不透明随机刷新令牌（数据库只保存其 SHA-256 哈希）。"""
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    """刷新令牌哈希（SHA-256），数据库不落明文。"""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _extract_bearer_token(request: Request) -> str | None:
    """从 Authorization 请求头提取 Bearer token；缺失返回 None。"""
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        return None
    token = authorization[len("Bearer "):].strip()
    return token or None


async def get_current_user_id(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> int:
    """FastAPI 鉴权依赖：校验通过后返回当前登录用户 ID。

    校验顺序：
    1. 是否为白名单请求路径 —— 是则直接放行（返回 0 表示匿名放行；
       受保护路由下不会命中白名单路径）；
    2. 请求头 Authorization: Bearer <token> 是否存在 —— 不存在返回 401；
    3. 校验 token 是否有效 —— 无效/过期返回 401。

    将本依赖注入到受保护路由（APIRouter(dependencies=[...]) 或
    参数 Depends(get_current_user_id)）即可对后续每次请求做鉴权拦截。
    """
    # 1. 白名单直接放行
    if is_whitelisted(request.url.path):
        return 0

    # 2. 获取请求头 token，不存在则 401
    token = credentials.credentials if credentials is not None else _extract_bearer_token(request)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录或登录已过期，请先登录",
        )

    # 3. 校验 token 有效性，无效则 401
    return decode_access_token(token)
