# 劳翼法务 —— 劳动法规检索与 AI 法律咨询平台（毕设）

基于「法规 RAG 检索 + 大模型问答」的劳动法律咨询平台。用户注册登录后，
可在对话中描述劳动法律问题（欠薪、辞退、加班费、工伤、仲裁时效等），
系统检索劳动法规知识库，给出引用真实法条的解答，条文可点击查看原文。

> 技术栈：React 18 + AntD 5（前端）/ FastAPI + LangGraph + Milvus（后端）

## 核心能力

- **劳动法规 RAG 检索**：6 部劳动法规按条文级分块入库（Milvus 向量库 + PostgreSQL 元数据），语义检索相关条文。
- **AI 法律咨询**：多轮对话，意图路由 → 法规问答 Agent → 调用检索工具 → 流式返回回答，回答中标注 `[ref-xxx]` 引用标记。
- **法条引用溯源**：每条回答附带引用来源卡片（法规名 / 条文号 / 章节 / 法条原文），点击可展开查看。
- **用户注册登录（双 token 鉴权）**：argon2 密码哈希 + JWT 双 token 机制（短时 access token + 长效 refresh token），
  受保护接口统一经过 `app/security.py` 的鉴权依赖拦截（白名单放行 / 缺 token 401 / 无效 token 401），
  前端对每次请求自动携带 Bearer token，401 时自动用刷新令牌续期并重试，续期失败跳转登录页。
- **会话管理**：新建 / 重命名 / 删除咨询会话，历史消息自动保存。

## 目录结构

```
agent-service/            FastAPI + LangGraph 后端
  app/security.py         统一安全模块：白名单 / JWT 双 token 签发与校验 / 鉴权依赖（get_current_user_id）
  app/agents/             intent_router（意图路由）/ orchestrator（主 Graph）/ legal_qa（法规问答）/ chitchat
  app/agents/tools.py     query_legal_provision（法规检索工具，输出 clause_sources）
  app/modules/chat/       对话接口（SSE 流式）
  app/modules/chat_thread/ 会话管理接口
  app/modules/user/       注册/登录/刷新/登出接口 + refresh_tokens 表
  app/rag/                KnowledgeChunk 条文级 RAG（pipeline 分块 / retriever 检索 / repository）
  data/legal/             6 部劳动法规文本（入库语料）
  scripts/ingest_rag.py   法规入库脚本（按条文分块 → Milvus + PostgreSQL）
  tests/                  pytest 单元测试（认证 / 双 token / 鉴权依赖）
insurance-web/            React + AntD 5 前端
  src/AdvisorPage.tsx     咨询对话页（会话列表 + 多轮对话 + 法条引用展示）
  src/HomePage.tsx        首页（定位 + 登录注册入口）
  src/AuthModal.tsx       登录/注册弹窗
  src/api.ts              后端 API 封装（自动携带 Bearer token + 401 自动刷新重试）
  src/auth.ts             本地会话存储（access token + refresh token）
  src/types.ts            类型定义
deploy/                   postgres 初始化 SQL、milvus、docker-compose（基础设施）
docs/                     测试报告等文档
```

## 数据库表（由 deploy/postgres/init 建）

- `users`（用户，argon2 密码哈希）
- `refresh_tokens`（双 token 机制的刷新令牌，仅存 SHA-256 哈希，刷新时轮换撤销）
- `chat_threads`（咨询会话）
- `chat_messages`（对话消息，含 additional_info 法条引用）
- `knowledge_chunks`（RAG 条文块，PostgreSQL 存元数据 + 原文，Milvus 存向量）

## 运行 / 验证

### 1. 基础设施

需要 PostgreSQL 16 + Milvus 2.x。可用 `deploy/docker-compose.yml` 一键启动，
或使用已有虚拟机。建库后执行 `deploy/postgres/init/` 下的 SQL 初始化表结构。

> Milvus 的 rerank 服务配置（`deploy/milvus/user.yaml`）包含 DashScope API Key，
> 已加入 `.gitignore` 不随仓库分发；首次运行请复制 `user.yaml.example` 并填入自己的 Key。


> 已有旧库升级：执行 `deploy/postgres/init/03-auth-docs-upgrade.sql`（幂等）即可补充
> `refresh_tokens` 新表，无需重建数据库。

### 2. 配置环境变量

复制 `agent-service/.env.example` 为 `.env`，填写：

```
DB_HOST / DB_PORT / DB_NAME / DB_USER / DB_PASSWORD   # PostgreSQL 连接
MILVUS_HOST / MILVUS_PORT                               # Milvus 连接
DEEPSEEK_API_KEY / CHAT_MODEL                            # 大模型 API
DASHSCOPE_API_KEY                                        # 文本嵌入（DashScope text-embedding-v4）
JWT_SECRET                                               # JWT 签名密钥
JWT_ACCESS_EXPIRE_MINUTES / JWT_REFRESH_EXPIRE_DAYS      # 双 token 有效期（默认 120 分钟 / 7 天）
```

### 3. 启动后端

```bash
cd agent-service
uv sync
uv run python -m app.main
```

> Windows 下必须用 `python -m app.main`（内部切换 Selector 事件循环），
> 不要直接用 `uvicorn app.main:app`（会因 ProactorEventLoop 导致数据库连接失败）。

自检：`GET http://127.0.0.1:8001/health` 返回 `{"status":"ok"}`。
接口文档：`http://127.0.0.1:8001/docs`（受保护接口带 Authorize 按钮，填登录返回的 access token）。

### 4. 导入法规知识库（首次运行必做）

```bash
cd agent-service
uv run python scripts/ingest_rag.py
```

脚本读取 `data/legal/*.md`（6 部法规），按条文级分块后写入 Milvus（向量）
和 PostgreSQL（knowledge_chunks 元数据）。重复运行会先清空旧数据再导入。

### 5. 启动前端

```bash
cd insurance-web
npm install
npm run dev
```

打开 http://localhost:5173 。前端开发服务器代理 `/api` 到后端 8001 端口。

### 6. 演示账号

数据库初始化后预置演示账号：**用户名 `骆智鹏`，密码 `123456`**。
也可在登录页点击"注册"自行创建账号。

## 接口一览（部分）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | /api/v1/auth/register | 注册（返回 access + refresh 双 token） |
| POST | /api/v1/auth/login | 登录（返回 access + refresh 双 token） |
| POST | /api/v1/auth/refresh | 刷新令牌（轮换 refresh token，签发新 access token） |
| POST | /api/v1/auth/logout | 退出登录（撤销 refresh token） |
| POST | /api/v1/chat | AI 对话（SSE 流式，需 Bearer token） |
| GET/POST | /api/v1/chat-threads | 会话列表 / 新建（需 Bearer token） |

## 鉴权设计（三大校验步骤）

`app/security.py` 提供 `get_current_user_id` 依赖，注入受保护路由后对每次请求做鉴权拦截：

1. **白名单判断**：`/health`、`/docs`、`/api/v1/auth/login|register|refresh|logout` 等直接放行；
2. **token 存在性**：读取请求头 `Authorization: Bearer <token>`，缺失返回 401；
3. **token 有效性**：校验 JWT 签名、类型与过期时间，无效/过期返回 401。

前端 `src/api.ts` 统一在请求头附带 access token；收到 401 后先用 refresh token
调用 `/auth/refresh` 自动续期并重试原请求，续期也失败则清空本地会话并跳转登录页。

## 测试

```bash
# 后端单元测试（认证 / 双 token 轮换 / 鉴权依赖）
cd agent-service && uv run pytest

# 前端类型检查 + 生产构建
cd insurance-web && npm run build
```

## 说明

- 法规解答含**免责提示**：内容仅供咨询参考，重大涉诉事项请咨询执业律师。
- 本机无 Docker/远程库时，只能做编译级自验（`compileall` / `pytest` / `npm run build`）；
  端到端运行需 PostgreSQL + Milvus 就绪。
