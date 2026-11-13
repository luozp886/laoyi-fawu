import json
import re

from langchain.tools import tool
from langgraph.config import get_stream_writer

from app.core.logging import get_logger

logger = get_logger(__name__)


def _extract_clause_no(section_path, content: str | None = None) -> str | None:
    """从章节路径中提取条文号，如“第X条”；章节路径里没有时尝试从法条正文开头提取"""
    if isinstance(section_path, str):
        text = section_path
    elif isinstance(section_path, (list, tuple)):
        text = "/".join(str(part) for part in section_path)
    else:
        text = ""
    match = re.search(r"第[一二三四五六七八九十百零〇0-9]+条", text)
    if match:
        return match.group(0)
    if content:
        match = re.search(r"^\s*(第[一二三四五六七八九十百零〇0-9]+条)", content)
        if match:
            return match.group(1)
    return None


@tool
async def query_legal_provision(query: str) -> str:
    """从劳动法规知识库检索相关法条。回答法律问题时先调用本工具，再依据检索结果作答。"""
    from app.rag import retriever

    # 关键：工具内部必须兜住所有异常，绝不能向外抛。
    # 一旦工具抛异常，Agent 图会崩溃，历史里会残留"只调用了工具但没结果"的
    # 半截消息，下次对话模型会因 tool_calls 无对应结果而报 400。
    try:
        chunks = await retriever.retrieve(query, 5)
    except Exception:
        logger.warning("法规检索失败，已返回友好提示", exc_info=True)
        return "检索知识库暂时不可用，请稍后重试，或换个说法描述您的问题。"

    if not chunks:
        return "没有检索到相关法条。"

    sources = []
    for i, chunk in enumerate(chunks, start=1):
        clause_no = _extract_clause_no(chunk.section_path, chunk.content)
        sources.append(
            {
                "source_id": f"ref-{i:03d}",
                "document_name": chunk.doc_title,
                "clause_name": f"{chunk.doc_title}{('·' + clause_no) if clause_no else ''}",
                "section_path": chunk.section_path,
                "clause_no": clause_no,
                "content": chunk.content,
            }
        )
    writer = get_stream_writer()
    writer({"type": "additional_info", "data": {"type": "clause_sources", "sources": sources}})
    return json.dumps(sources, ensure_ascii=False)
