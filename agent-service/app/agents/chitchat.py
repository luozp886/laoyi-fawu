from typing import NotRequired

from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, SystemMessage
from langgraph.graph import StateGraph

from app.agents.schemas import LegalAgentState
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


SYSTEM_MESSAGE = """
你是法律咨询平台的智能助手，负责处理与劳动法律业务无关的普通聊天。

要求：
1. 回复友好、自然，最多两句话。
2. 不假装有个人经历、情感、实时信息或外部能力。
3. 不提供医疗等高风险专业建议；涉及具体案件的，引导回到劳动法律咨询。
4. 每次回复都自然引导用户咨询劳动法律问题。
5. 超出能力范围时，如实说明无法提供。
""".strip()

MAX_CHITCHAT_COUNT = 3


class ChitchatState(LegalAgentState):
    """闲聊子 Agent 状态"""

    chitchat_count: NotRequired[int]


class ChitchatAgent:

    def __init__(self) -> None:
        self.model = init_chat_model(
            model=settings.llm.chat_model,
            model_provider="deepseek",
            api_key=settings.llm.api_key,
            extra_body={"thinking": {"type": "disabled"}},
        )

    async def handle_chitchat(self, state: ChitchatState) -> dict:
        count = state.get("chitchat_count", 0)
        if state.get("previous_workflow") != "chitchat":
            count = 0
        logger.info("处理闲聊消息", chitchat_count=count)

        if count >= MAX_CHITCHAT_COUNT:
            return {
                "messages": [
                    AIMessage("我主要协助处理劳动法律咨询与文书生成，请告诉我您遇到的问题或想办理的事项。")
                ]
            }

        response = await self.model.ainvoke(
            [SystemMessage(content=SYSTEM_MESSAGE), *state["messages"]]
        )
        return {"messages": [response], "chitchat_count": count + 1}

    def build(self):
        builder = StateGraph(ChitchatState)
        builder.add_node("handle_chitchat", self.handle_chitchat)
        builder.set_entry_point("handle_chitchat")
        builder.set_finish_point("handle_chitchat")
        return builder.compile(checkpointer=True)


def init_chitchat_agent():
    return ChitchatAgent().build()
