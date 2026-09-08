from typing import NotRequired

from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph

from app.agents.schemas import InsuranceAgentState
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


SYSTEM_PROMPT = """
你是保险理赔咨询专员，专门处理理赔相关咨询，包括报案、理赔流程、理赔材料、理赔责任和理赔进度等。

要求：
1. 当用户信息不足时，应主动追问并收集必要信息：险种、出险时间、事故简单情况。
2. 用户询问是否符合理赔责任或能否获赔时，禁止承诺赔付，应如实说明最终以保险公司的正式理赔审核结果为准。
3. 当用户信息不足时暂不给出理赔结论，先补齐信息；信息推断不充分时不要下断言。
4. 回答要简短、精确，不要长篇大论。
5. 不编造保险条款，涉及具体保单、进度或金额而无依据时，引导用户补充或建议转人工处理。
6. 用户话题完全偏离理赔咨询时，交由上层主Graph路由处理。
""".strip()


class ClaimAgentState(InsuranceAgentState):
    """理赔咨询子Agent状态"""

    # whether已经把"险种/出险时间/事故情况"必要信息收集齐
    has_basic_info: NotRequired[bool]


class ClaimAgent:
    """理赔咨询子Agent，与闲聊子Agent保持相同的手写StateGraph形态"""

    def __init__(self) -> None:
        self.model = init_chat_model(
            model=settings.llm.chat_model,
            model_provider="deepseek",
            api_key=settings.llm.api_key,
            extra_body={"thinking": {"type": "disabled"}},
        )

    async def handle_claim(self, state: ClaimAgentState) -> dict:
        # 复用 / 重置该会话是否已收集齐基本信息
        has_basic_info = state.get("has_basic_info", False)
        if state.get("previous_workflow") != "claim":
            has_basic_info = False
        logger.info("处理理赔咨询", has_basic_info=has_basic_info)

        response = await self.model.ainvoke(
            [SystemMessage(content=SYSTEM_PROMPT), *state["messages"]]
        )
        return {"messages": [response], "has_basic_info": has_basic_info}

    def build(self):
        builder = StateGraph(ClaimAgentState)
        builder.add_node("handle_claim", self.handle_claim)
        builder.set_entry_point("handle_claim")
        builder.set_finish_point("handle_claim")

        # 使用父Graph提供的Checkpointer，保存子图私有状态
        return builder.compile(checkpointer=True)


def init_claim_agent():
    return ClaimAgent().build()
