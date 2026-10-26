import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.agents.orchestrator import init_legal_orchestrator
from app.core.config import settings
from app.core.exceptions import ApplicationError
from app.core.logging import configure_logging, get_logger
from app.infra.checkpointer import close_checkpointer, init_checkpointer
from app.modules.chat.router import router as chat_router
from app.modules.chat_thread.router import router as chat_thread_router
from app.modules.user.router import router as user_router


# 生命周期管理（预留）
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"【{settings.app.name}】应用启动中...")
    from app.infra.database import check_database, close_database
    from app.rag import close_rag  # 导入模块就会初始化
    try:
        # 1.检查业务数据库连接
        await check_database()
        # 2.初始化Checkpointer连接池
        checkpointer = await init_checkpointer()
        # 3.初始化法律顾问主Graph
        app.state.agent = init_legal_orchestrator(checkpointer)
        yield
    finally:
        logger.info("应用关闭中... ")
        # 4.关闭Checkpointer连接池
        await close_checkpointer()
        # 5.关闭SQLAlchemy连接池
        await close_database()
        # 6.关闭RAG系统
        close_rag()

# 初始化日志系统
configure_logging(settings.logging.level)
logger = get_logger(__name__)

app = FastAPI(
    title=settings.app.name,
    debug=settings.app.debug,
    lifespan=lifespan,
)

app.include_router(chat_router)
app.include_router(chat_thread_router)
app.include_router(user_router)


# 统一处理业务异常：只要继承自 ApplicationError，都会转换成统一格式的 HTTP 响应
@app.exception_handler(ApplicationError)
async def handle_application_error(
    request: Request,
    exc: ApplicationError,  # 捕获到的异常（这里用自定义异常基类捕获，所有业务异常都会匹配到）
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,  # 异常中自带status
        content={
            "code": exc.code,        # 异常中自带code
            "message": exc.message,  # 异常中自带message
        },
    )


# 兜底处理所有未预期的异常（数据库错误、KeyError 等）：
# 记录完整堆栈供排查，返回统一的 JSON 错误而不是默认的 HTML 堆栈页，
# 避免把内部实现细节暴露给前端，也让用户看到友好提示而不是白屏。
@app.exception_handler(Exception)
async def handle_unexpected_error(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.exception(
        "未捕获异常 path=%s method=%s",
        request.url.path,
        request.method,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={
            "code": "INTERNAL_ERROR",
            "message": "服务器内部错误，请稍后重试或联系管理员",
        },
    )

# CORS配置，解决跨域问题
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", summary="健康检测接口")
async def health_check() -> dict[str, str]:
    logger.info("执行健康检查")
    return {"status": "ok"}

if __name__ == "__main__":
# Windows 下必须用 SelectorEventLoop（psycopg 异步驱动无法在 ProactorEventLoop 上运行，
# 否则 chat 会话持久化会失败）。请以 `uv run python -m app.main` 启动（勿用 uvicorn 命令行）。
    uvicorn.run(
        "app.main:app",
        host=settings.app.host,
        port=settings.app.port,
        reload=False,
        loop="asyncio:SelectorEventLoop" if sys.platform == "win32" else "auto",
    )
