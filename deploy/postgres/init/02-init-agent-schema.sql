-- 劳动法律智能咨询平台 —— agent/对话库 schema
-- chat_threads：会话元数据（LangGraph Checkpointer 存消息正文）
-- knowledge_chunks：父知识块（RAG 用），以“知识文档 doc_id”为粒度，对应某部法律法规

CREATE TABLE IF NOT EXISTS chat_threads (
    id UUID PRIMARY KEY,
    user_id BIGINT NOT NULL,
    title VARCHAR(200) NOT NULL DEFAULT '新会话',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chat_threads_user_updated
    ON chat_threads(user_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id UUID PRIMARY KEY,
    doc_id BIGINT NOT NULL,                -- 知识文档主键（某部法规，对应 data/documents 目录）
    doc_title VARCHAR(300) NOT NULL,       -- 文档标题，如《中华人民共和国劳动合同法》
    section_path TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_doc
    ON knowledge_chunks(doc_id);

COMMENT ON TABLE chat_threads IS '用户与智能客服的会话元数据，消息正文由 LangGraph Checkpointer 保存';
COMMENT ON COLUMN chat_threads.id IS '会话主键，同时作为 LangGraph thread_id';
COMMENT ON COLUMN chat_threads.user_id IS 'JWT 中解析出的业务用户主键';

COMMENT ON TABLE knowledge_chunks IS '用于完整上下文和引用展示的父知识块(RAG)';
COMMENT ON COLUMN knowledge_chunks.doc_id IS '关联的知识文档(某部法规)主键';
COMMENT ON COLUMN knowledge_chunks.doc_title IS '文档标题(法规名称)';
COMMENT ON COLUMN knowledge_chunks.section_path IS '章节层级路径';
COMMENT ON COLUMN knowledge_chunks.content IS '父块完整正文';
