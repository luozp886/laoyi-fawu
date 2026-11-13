from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    """注册请求"""
    username: str = Field(min_length=2, max_length=80, description="用户名")
    password: str = Field(min_length=6, max_length=64, description="密码（至少 6 位）")
    email: str = Field(min_length=5, max_length=160, description="邮箱")
    display_name: str | None = Field(default=None, max_length=100, description="昵称")


class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(min_length=1, max_length=80, description="用户名")
    password: str = Field(min_length=1, max_length=64, description="密码")


class UserInfo(BaseModel):
    """登录态用户信息"""
    id: int
    username: str
    email: str
    display_name: str | None = None


class AuthResponse(BaseModel):
    """登录/注册成功响应（双 token：access + refresh）"""
    token: str = Field(description="访问令牌（JWT，短时有效）")
    refresh_token: str = Field(description="刷新令牌（长效，用于自动续期）")
    token_type: str = Field(default="bearer", description="令牌类型")
    user: UserInfo


class RefreshRequest(BaseModel):
    """刷新令牌请求"""
    refresh_token: str = Field(min_length=1, description="刷新令牌")


class LogoutRequest(BaseModel):
    """退出登录请求（撤销刷新令牌）"""
    refresh_token: str = Field(min_length=1, description="刷新令牌")
