from collections.abc import AsyncIterator

from fastapi.sse import ServerSentEvent
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph.state import CompiledStateGraph
from langgraph.stream import CustomTransformer
from langgraph.types import Command
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.schemas import AdditionalInfo
from app.modules.chat.schemas import ChatRequest
from app.modules.chat_thread.exceptions import ChatThreadNotFoundError
from app.modules.chat_thread.repository import ChatThreadRepository
from app.core.logging import get_logger


logger = get_logger(__name__)


class ChatService:
    def __init__(self, session: AsyncSession, agent: CompiledStateGraph):
        self.repository = ChatThreadRepository(session)
        self.agent = agent

    async def stream_chat(
        self,
        user_id: int,
        request: ChatRequest,
    ) -> AsyncIterator[ServerSentEvent]:
        # 1.校验会话是否属于当前用户
        thread = await self.repository.find_owned(
            request.thread_id,
            user_id,
        )
        if thread is None:
            raise ChatThreadNotFoundError

        # 2.校验通过后，调用Agent

        # 2.1.准备Agent输入
        if request.decision:
            # 有decision，说明是在恢复上一次中断，而不是新的一轮对话
            _input = Command(resume=request.decision)
        else:
            _input = {"messages": [HumanMessage(content=request.message)]}

        config = {"configurable": {"thread_id": str(request.thread_id)}}

        # 2.2.使用v3协议获取异步事件流
        stream = await self.agent.astream_events(
            _input,
            config,
            context={"user_id": user_id},
            version="v3",
            transformers=[CustomTransformer],
        )

        # 2.2.1.记录AIMessage的ID和引用信息
        final_message_id: str | None = None
        additional_info: AdditionalInfo = {}

        # 2.3.统一处理主Graph和子Graph的event事件
        async for event in stream:
            method = event["method"]
            # 判断事件类型，可以是messages、custom等等
            if method == "messages":
                data = event["params"]["data"][0]
                if isinstance(data, AIMessage):
                    # 手动返回AIMessage的情况（如主Graph的fallback、转人工节点）
                    yield ServerSentEvent(data=data.content, event="message")
                elif data.get("delta") and data["delta"].get("text"):
                    # 流式文本增量（如子Agent的逐字输出）
                    yield ServerSentEvent(data=data["delta"].get("text"), event="message")
                elif data.get("event") == "message-start" and data.get("id"):
                    # 第一个消息片段会传递Message的id
                    final_message_id = data.get("id")

            if method == "custom":
                data = event["params"]["data"]
                if isinstance(data, dict) and data.get("type") == "additional_info":
                    additional_info = data.get("data", {})
                    yield ServerSentEvent(data=additional_info, event="additional_info")

        # 2.4.处理中断（如保险方案待用户确认）
        interrupts = await stream.interrupts()
        for item in interrupts:
            yield ServerSentEvent(data=item.value, event="interrupt")

        # 2.5.把引用信息保存到State，方便查询历史消息时恢复
        if final_message_id and additional_info:
            await self.agent.aupdate_state(
                config,
                {"additional_info": {final_message_id: additional_info}},
            )

        # 2.6.返回结束标识
        yield ServerSentEvent(data="[DONE]", event="done")
