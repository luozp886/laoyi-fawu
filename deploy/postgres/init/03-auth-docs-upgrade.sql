-- 增量升级脚本：为已初始化的数据库补充“双 token 刷新”与“劳务文档维护”相关表。
-- 幂等，可重复执行：
--   psql -h <DB_HOST> -U <DB_USER> -d <DB_NAME> -f 03-auth-docs-upgrade.sql

-- ==== 登录刷新令牌（双 token 机制：refresh token 只存 SHA-256 哈希） ====
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE,
    replaced_by VARCHAR(64),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_hash ON refresh_tokens(token_hash);

-- ==== 劳务文档维护（上传后父子块入库 RAG 知识库） ====
CREATE TABLE IF NOT EXISTS law_documents (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(300) NOT NULL,
    category VARCHAR(50) NOT NULL DEFAULT 'other',
    file_name VARCHAR(255),
    source VARCHAR(300),
    content TEXT NOT NULL,
    rag_status VARCHAR(30) NOT NULL DEFAULT 'pending',
    rag_error TEXT,
    uploaded_by BIGINT NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_law_documents_rag_status CHECK (rag_status IN ('pending', 'ingested', 'failed'))
);
CREATE INDEX IF NOT EXISTS idx_law_documents_updated ON law_documents(updated_at DESC);

-- 文档自增 id 从 100 开始，避开内置法规知识库占用的 doc_id 1~6，防止上传文档覆盖内置法规索引
SELECT setval(pg_get_serial_sequence('law_documents', 'id'), 100, true);

COMMENT ON TABLE refresh_tokens IS '登录刷新令牌（双token机制，仅存SHA-256哈希，刷新时轮换）';
COMMENT ON TABLE law_documents IS '劳务文档维护：上传/维护后自动父子块入库 RAG 知识库';

