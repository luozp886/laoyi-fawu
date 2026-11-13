from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

from app.agents.tools import query_legal_provision
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


SYSTEM_PROMPT = """
你是“劳动法律知识助手”，负责回答劳动法律条文的咨询（工时、加班费、解除补偿、未签合同二倍工资、工伤认定与待遇、仲裁程序及时效等）。

要求：
1. 回答劳动法条问题前，先调用 query_legal_provision 检索法条，再依据检索结果回答。
2. 直接输出中文回答正文，不要输出“我先检索”“让我查一下”之类的过程说明或英文思考。
3. 引用检索到的法条时，在引用处标注对应的 [ref-001] 编号（与工具返回的 source_id 一致），不要编造法条编号、内容或金额标准；检索不到就如实说明。
4. 涉及个案能否获赔/如何操作时，提示属咨询性质、最终以仲裁委/法院及律师意见为准。
5. 回答简短、精确；完全偏离劳动法咨询的话题，交由上层主 Graph 路由。
"""


def init_legal_qa():
    """初始化劳动法规问答子 Agent"""
    model = init_chat_model(
        model=settings.llm.chat_model,
        model_provider="deepseek",
        api_key=settings.llm.api_key,
        extra_body={"thinking": {"type": "disabled"}},
    )
    agent = create_agent(
        model=model,
        tools=[query_legal_provision],
        system_prompt=SYSTEM_PROMPT,
        checkpointer=True,
        name="legal_qa",
    )
    logger.info("劳动法规问答子 Agent 初始化成功")
    return agent
