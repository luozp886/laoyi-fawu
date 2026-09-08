from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.chat_thread.exceptions import ChatThreadNotFoundError
from app.modules.chat_thread.schemas import (
    ChatHistoryResponse,
    ChatMessageResponse,
)
from .models import ChatThread
from .repository import ChatThreadRepository

class ChatThreadService:
    def __init__(
        self,
        session: AsyncSession,
        agent: CompiledStateGraph,
    ):
        self.session = session
        self.repository = ChatThreadRepository(session)
        self.agent = agent

    async def add(self, user_id: int, title: str):
        # 用上下文管理，开启事务，运行完成，自动commit，出现异常，自动rollback
        async with self.session.begin():
            # 创建会话对象，封装要插入的数据
            chat_thread = ChatThread(user_id=user_id, title=title)
            # 调用repository的add方法，将数据插入数据库
            await self.repository.add(chat_thread)
            # 返回新创建的会话对象
            return chat_thread

    async def list_by_user(self, user_id: int) -> list[ChatThread]:
        return await self.repository.list_by_user(user_id)

    async def rename(
        self,
        thread_id: UUID,
        user_id: int,
        title: str
    ) -> ChatThread:
        async with self.session.begin():
            # 1.根据thread_id和user_id查询会话信息
            thread = await self.repository.find_owned(thread_id, user_id)
            if thread is None:
                # 为None，说明不存在，或者不属于当前用户，抛出异常
                raise ChatThreadNotFoundError

            # 2.查询后直接修改字段，触发数据库更新
            thread.title = title

            # 3.刷新数据，重新从数据库中查出最新值
            await self.session.flush()
            await self.session.refresh(thread)

        return thread

    async def get_history(
        self,
        thread_id: UUID,
        user_id: int,
    ) -> ChatHistoryResponse:
        # 1.校验会话归属
        thread = await self.repository.find_owned(thread_id, user_id)
        if thread is None:
            raise ChatThreadNotFoundError

        # 2.读取Agent最新状态
        config = {"configurable": {"thread_id": str(thread_id)}}
        snapshot = await self.agent.aget_state(config)

        # 3.读取additional_info（按AI消息id保存的引用来源）
        additional_infos = snapshot.values.get("additional_info", {})

        # 4.处理消息历史
        messages = []
        for message in snapshot.values.get("messages", []):
            # 4.1.只保留用户消息和AI消息
            if isinstance(message, HumanMessage):
                role = "user"
            elif isinstance(message, AIMessage):
                role = "assistant"
            else:
                continue

            # 4.2.组装信息
            if message.text:
                messages.append(
                    ChatMessageResponse(
                        role=role,
                        content=message.text,
                        additional_info=additional_infos.get(message.id),
                    )
                )

        # 5.处理interrupt
        interrupts = None
        if hasattr(snapshot, "interrupts") and snapshot.interrupts:
            interrupts = snapshot.interrupts
        elif hasattr(snapshot, "tasks") and snapshot.tasks:
            for task in snapshot.tasks:
                if hasattr(task, "interrupts") and task.interrupts:
                    interrupts = task.interrupts
                    break

        return ChatHistoryResponse(
            thread_id=thread_id,
            messages=messages,
            interrupt=interrupts[0].value if interrupts else None,
        )

    async def delete(
        self,
        thread_id: UUID,
        user_id: int,
    ) -> None:
        async with self.session.begin():
            # 1.校验会话归属
            thread = await self.repository.find_owned(thread_id, user_id)
            if thread is None:
                raise ChatThreadNotFoundError

            # 2.删除Checkpointer中的会话状态
            await self.agent.checkpointer.adelete_thread(str(thread_id))

            # 3.删除会话元数据
            await self.repository.delete(thread)
