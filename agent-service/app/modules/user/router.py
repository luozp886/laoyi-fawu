from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ApplicationError
from app.infra.database import get_session
from app.modules.user.models import User
from app.modules.user.schemas import (
    AuthResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    UserInfo,
)
from app.modules.user.service import (
    issue_refresh_token,
    login_user,
    register_user,
    revoke_refresh_token,
    rotate_refresh_token,
)
from app.security import create_access_token

router = APIRouter(prefix="/api/v1/auth", tags=["认证接口"])


def _build_auth_response(user: User, refresh_token: str) -> AuthResponse:
    """组装双 token 登录响应：短时 access token + 长效 refresh token。"""
    return AuthResponse(
        token=create_access_token(user.id),
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserInfo(
            id=user.id,
            username=user.username,
            email=user.email,
            display_name=user.display_name,
        ),
    )


@router.post("/register", response_model=AuthResponse, summary="注册账号")
async def register(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_session),
) -> AuthResponse:
    try:
        user = await register_user(
            session,
            username=body.username,
            password=body.password,
            email=body.email,
            display_name=body.display_name,
        )
    except ApplicationError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc
    refresh_token = await issue_refresh_token(session, user.id)
    await session.commit()
    return _build_auth_response(user, refresh_token)


@router.post("/login", response_model=AuthResponse, summary="账号登录")
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> AuthResponse:
    try:
        user = await login_user(session, username=body.username, password=body.password)
    except ApplicationError as exc:
        raise HTTPException(status_code=401, detail=exc.message) from exc
    refresh_token = await issue_refresh_token(session, user.id)
    await session.commit()
    return _build_auth_response(user, refresh_token)


@router.post("/refresh", response_model=AuthResponse, summary="刷新访问令牌（双token续期）")
async def refresh(
    body: RefreshRequest,
    session: AsyncSession = Depends(get_session),
) -> AuthResponse:
    """用长效 refresh token 换取新的 access token（并轮换 refresh token）。"""
    result = await rotate_refresh_token(session, body.refresh_token)
    if result is None:
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录")
    user_id, new_refresh_token = result
    user = await session.get(User, user_id)
    await session.commit()
    if user is None:
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录")
    return _build_auth_response(user, new_refresh_token)


@router.post("/logout", summary="退出登录（撤销刷新令牌）")
async def logout(
    body: LogoutRequest,
    session: AsyncSession = Depends(get_session),
):
    await revoke_refresh_token(session, body.refresh_token)
    await session.commit()
    return {"message": "退出成功"}

