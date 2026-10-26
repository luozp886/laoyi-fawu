from typing import Annotated

from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, Request
from fastapi.sse import EventSourceResponse, ServerSentEvent
from app.infra.database import get_session
from app.modules.chat.schemas import ChatRequest
from app.modules.chat.service import ChatService
from app.security import get_current_user_id


router = APIRouter(prefix="/api/v1/chat", tags=["与AI对话接口"])


def get_chat_service(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    # 1.创建ChatService
    agent = request.app.state.agent
    return ChatService(session, agent)

@router.post("", response_class=EventSourceResponse, summary="发送消息（SSE流式返回）")
async def chat(
    request: ChatRequest,
    # 通过依赖注入解析并校验 JWT，得到当前登录用户ID（替代原来的 x-user-id 请求头）
    user_id: Annotated[int, Depends(get_current_user_id)],
    service: ChatService = Depends(get_chat_service),
):
    # Generator, 用yield不断生成内容，形成动态列表
    async for sse in service.stream_chat(user_id, request):
        yield sse
