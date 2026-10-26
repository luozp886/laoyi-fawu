import {
  ArrowLeftOutlined,
  CustomerServiceOutlined,
  DeleteOutlined,
  EditOutlined,
  MessageOutlined,
  FilePdfOutlined,
  PlusOutlined,
  SafetyCertificateOutlined,
  SendOutlined,
} from '@ant-design/icons';
import { Alert, Button, Drawer, Empty, Input, Modal, Popconfirm, Spin } from 'antd';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { attachInfoToLastAssistantMessage, normalizeAdditionalInfo } from './additionalInfo';
import {
  ApiError,
  createChatThread,
  deleteChatThread,
  getChatHistory,
  listChatThreads,
  renameChatThread,
  streamChat,
} from './api';
import { MarkdownMessage } from './MarkdownMessage';
import type { AdditionalInfo, AuthSession, ClauseSource } from './types';
import type { ChatMessage, ChatThread } from './types';

interface AdvisorPageProps {
  session: AuthSession;
  onBack: () => void;
  onSessionExpired: () => void;
}

export function AdvisorPage({ session, onBack, onSessionExpired }: AdvisorPageProps) {
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loadingThreads, setLoadingThreads] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [renamingThread, setRenamingThread] = useState<ChatThread | null>(null);
  const [renameTitle, setRenameTitle] = useState('');
  const [selectedSource, setSelectedSource] = useState<SelectedSource | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  const loadMessages = useCallback(async (threadId: string) => {
    setLoadingMessages(true);
    setError(null);
    try {
      const history = await getChatHistory(threadId);
      setMessages(normalizeHistoryMessages(history.messages));
    } catch (reason) {
      if (isUnauthorized(reason)) {
        onSessionExpired();
        return;
      }
      setError(reason instanceof Error ? reason.message : '会话历史加载失败');
    } finally {
      setLoadingMessages(false);
    }
  }, [onSessionExpired]);

  const openThread = useCallback(async (threadId: string) => {
    setActiveThreadId(threadId);
    await loadMessages(threadId);
  }, [loadMessages]);

  const createThread = useCallback(async () => {
    const thread = await createChatThread();
    setThreads((current) => [thread, ...current]);
    setActiveThreadId(thread.id);
    setMessages([]);
    return thread;
  }, []);

  async function startNewThread() {
    setError(null);
    try {
      await createThread();
    } catch (reason) {
      if (isUnauthorized(reason)) {
        onSessionExpired();
        return;
      }
      setError(reason instanceof Error ? reason.message : '新建会话失败');
    }
  }

  async function renameThread() {
    if (!renamingThread) return;
    const title = renameTitle.trim();
    if (!title) return;
    setError(null);
    try {
      const updated = await renameChatThread(renamingThread.id, title);
      setThreads((current) =>
        current.map((thread) => (thread.id === updated.id ? updated : thread)),
      );
      setRenamingThread(null);
      setRenameTitle('');
    } catch (reason) {
      if (isUnauthorized(reason)) {
        onSessionExpired();
        return;
      }
      setError(reason instanceof Error ? reason.message : '重命名会话失败');
    }
  }

  async function deleteThread(threadId: string) {
    setError(null);
    try {
      await deleteChatThread(threadId);
      const nextThreads = threads.filter((thread) => thread.id !== threadId);
      setThreads(nextThreads);
      if (activeThreadId === threadId) {
        const nextActive = nextThreads[0];
        setActiveThreadId(nextActive?.id ?? null);
        setMessages([]);
        if (nextActive) await loadMessages(nextActive.id);
      }
    } catch (reason) {
      if (isUnauthorized(reason)) {
        onSessionExpired();
        return;
      }
      setError(reason instanceof Error ? reason.message : '删除会话失败');
    }
  }

  useEffect(() => {
    let ignore = false;
    async function loadThreads() {
      setLoadingThreads(true);
      setError(null);
      try {
        const loaded = await listChatThreads();
        if (ignore) return;
        if (loaded.length === 0) {
          const thread = await createChatThread();
          if (ignore) return;
          setThreads([thread]);
          setActiveThreadId(thread.id);
          setMessages([]);
          return;
        }
        setThreads(loaded);
        setActiveThreadId(loaded[0].id);
        await loadMessages(loaded[0].id);
      } catch (reason) {
        if (!ignore) {
          if (isUnauthorized(reason)) {
            onSessionExpired();
            return;
          }
          setError(reason instanceof Error ? reason.message : '会话加载失败');
        }
      } finally {
        if (!ignore) setLoadingThreads(false);
      }
    }
    void loadThreads();
    return () => {
      ignore = true;
    };
  }, [loadMessages, onSessionExpired]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, sending]);

  async function sendMessage() {
    const content = input.trim();
    if (!content || sending) return;
    setInput('');
    setSending(true);
    setError(null);
    try {
      const threadId = activeThreadId ?? (await createThread()).id;
      setMessages((current) => [
        ...current,
        { role: 'user', content },
        { role: 'assistant', content: '' },
      ]);
      await streamChat(threadId, { message: content }, {
        onMessage: appendAssistantChunk,
        onAdditionalInfo: appendAdditionalInfo,
      });
      setThreads((current) =>
        current.map((thread) =>
          thread.id === threadId
            ? { ...thread, title: thread.title === '法律咨询' ? content.slice(0, 20) : thread.title }
            : thread,
        ),
      );
    } catch (reason) {
      if (isUnauthorized(reason)) {
        onSessionExpired();
        return;
      }
      setError(reason instanceof Error ? reason.message : '消息发送失败');
      setMessages((current) => current.filter((item) => item.content !== ''));
    } finally {
      setSending(false);
    }
  }

  function appendAssistantChunk(chunk: string) {
    setMessages((current) => {
      const next = [...current];
      const last = next[next.length - 1];
      if (last?.role === 'assistant') {
        next[next.length - 1] = { ...last, content: last.content + chunk };
      }
      return next;
    });
  }

  function appendAdditionalInfo(raw: unknown) {
    const info = normalizeAdditionalInfo(raw);
    setMessages((current) => attachInfoToLastAssistantMessage(current, info));
  }

  return (
    <div className="advisor-page">
      <header className="advisor-header">
        <div className="brand">
          <span className="brand__mark"><SafetyCertificateOutlined /></span>
          <span><strong>劳翼法务</strong><small>劳动法律顾问</small></span>
        </div>
        <div>
          <span>{session.user.displayName || session.user.username}</span>
          <Button icon={<ArrowLeftOutlined />} onClick={onBack}>返回首页</Button>
        </div>
      </header>
      <main className="advisor-workspace">
        <aside className="thread-panel">
          <Button block type="primary" icon={<PlusOutlined />} onClick={() => void startNewThread()}>
            新建咨询
          </Button>
          <div className="thread-list">
            {loadingThreads ? <Spin /> : null}
            {!loadingThreads && threads.length === 0 ? <Empty description="暂无会话" /> : null}
            {threads.map((thread) => (
              <div
                className={thread.id === activeThreadId ? 'thread-item is-active' : 'thread-item'}
                key={thread.id}
              >
                <button type="button" onClick={() => void openThread(thread.id)}>
                  <MessageOutlined />
                  <span className="thread-text">
                    <strong>{thread.title}</strong>
                    <small>{formatThreadTime(thread.created_at)}</small>
                  </span>
                </button>
                <div className="thread-actions">
                  <Button
                    type="text"
                    size="small"
                    icon={<EditOutlined />}
                    onClick={() => {
                      setRenamingThread(thread);
                      setRenameTitle(thread.title);
                    }}
                  />
                  <Popconfirm
                    title="删除会话"
                    description="删除后会同时清理该会话的历史状态。"
                    okText="删除"
                    cancelText="取消"
                    onConfirm={() => void deleteThread(thread.id)}
                  >
                    <Button type="text" danger size="small" icon={<DeleteOutlined />} />
                  </Popconfirm>
                </div>
              </div>
            ))}
          </div>
        </aside>

        <section className="chat-panel">
          <div className="chat-inner">
          {error ? <Alert className="chat-alert" type="error" showIcon message={error} /> : null}
          <div className="chat-scroll">
            {loadingMessages ? (
              <div className="chat-loading"><Spin /></div>
            ) : messages.length === 0 ? (
              <div className="chat-empty">
                <CustomerServiceOutlined />
                <h1>你好，我是劳翼法务的劳动法律咨询助手</h1>
                <p>输入你遇到的劳动法律问题（欠薪、被辞退、加班费、工伤、未签合同、仲裁时效等），我会检索相关法规，为你给出依据法条的解答。</p>
              </div>
            ) : (
              messages.map((message, index) => (
                <div className={`chat-message chat-message--${message.role}`} key={`${message.role}-${index}`}>
                  <div>
                    {message.content ? (
                      <MessageContent
                        message={message}
                        onSourceClick={(source, answerContent) =>
                          setSelectedSource({ source, answerContent })
                        }
                      />
                    ) : '正在整理回复...'}
                  </div>
                </div>
              ))
            )}
            <div ref={bottomRef} />
          </div>
          <div className="chat-composer">
            <Input.TextArea
              value={input}
              autoSize={{ minRows: 1, maxRows: 4 }}
              placeholder="例如：公司拖欠我 3 个月工资，我能要回吗？经济补偿金怎么算？"
              disabled={sending}
              onChange={(event) => setInput(event.target.value)}
              onPressEnter={(event) => {
                if (!event.shiftKey) {
                  event.preventDefault();
                  void sendMessage();
                }
              }}
            />
            <Button type="primary" icon={<SendOutlined />} loading={sending} onClick={() => void sendMessage()}>
              发送
            </Button>
          </div>
          </div>
        </section>
      </main>
      <Modal
        open={renamingThread !== null}
        title="重命名会话"
        okText="保存"
        cancelText="取消"
        onOk={() => void renameThread()}
        onCancel={() => {
          setRenamingThread(null);
          setRenameTitle('');
        }}
      >
        <Input
          value={renameTitle}
          maxLength={80}
          placeholder="请输入会话名称"
          onChange={(event) => setRenameTitle(event.target.value)}
          onPressEnter={() => void renameThread()}
        />
      </Modal>
      <Drawer
        open={selectedSource !== null}
        title="条款引用"
        width={680}
        onClose={() => setSelectedSource(null)}
      >
        {selectedSource ? (
          <ClauseSourceDetail
            answerContent={selectedSource.answerContent}
            source={selectedSource.source}
          />
        ) : null}
      </Drawer>
    </div>
  );
}

function MessageContent({
  message,
  onSourceClick,
}: {
  message: ChatMessage;
  onSourceClick: (source: ClauseSource, answerContent: string) => void;
}) {
  const sources = extractClauseSources(message.additionalInfo);
  const sourceRefs = buildSourceRefs(message.content, sources);
  const sourceById = new Map(sources.map((source) => [source.source_id, source]));
  return (
    <>
      <MarkdownMessage
        content={message.content}
        sourceRefs={sourceRefs.map((item) => ({ sourceId: item.source.source_id, number: item.number }))}
        onSourceClick={(sourceId) => {
          const source = sourceById.get(sourceId);
          if (source) onSourceClick(source, message.content);
        }}
      />
      {sourceRefs.length ? (
        <div className="source-list">
          <strong>引用来源</strong>
          {sourceRefs.map((item) => (
            <button
              key={item.source.source_id}
              type="button"
              onClick={() => onSourceClick(item.source, message.content)}
            >
              <span>[{item.number}]</span>
              <FilePdfOutlined />
              <span>{sourceReferenceLabel(item.source)}</span>
            </button>
          ))}
        </div>
      ) : null}
    </>
  );
}

function extractClauseSources(info: AdditionalInfo[] | undefined): ClauseSource[] {
  return (info ?? [])
    .filter((item): item is Extract<AdditionalInfo, { type: 'clause_sources' }> =>
      item.type === 'clause_sources',
    )
    .flatMap((item) => item.sources);
}

function buildSourceRefs(content: string, sources: ClauseSource[]) {
  return sources
    .map((source) => {
      const index = findSourceIndex(content, source.source_id);
      return index >= 0 ? { source, index } : null;
    })
    .filter((item): item is { source: ClauseSource; index: number } => item !== null)
    .sort((left, right) => left.index - right.index)
    .map((item, index) => ({ ...item, number: index + 1 }));
}

function findSourceIndex(content: string, sourceId: string): number {
  const pattern = new RegExp(`\\[?${escapeRegExp(sourceId)}\\]?`);
  return content.search(pattern);
}

interface SelectedSource {
  source: ClauseSource;
  answerContent: string;
}

function ClauseSourceDetail({
  source,
  answerContent,
}: {
  source: ClauseSource;
  answerContent: string;
}) {
  const highlightedBlocks = buildHighlightedBlocks(answerContent, source);
  return (
    <div className="clause-source-detail">
      <div className="clause-source-header">
        <FilePdfOutlined />
        <div>
          <h3>{documentName(source)}</h3>
          <dl>
            {source.clause_no ? (
              <div>
                <dt>条文</dt>
                <dd>{source.clause_no}</dd>
              </div>
            ) : null}
            {source.section_path ? (
              <div>
                <dt>章节</dt>
                <dd>
                  <SectionPath value={source.section_path} />
                </dd>
              </div>
            ) : null}
          </dl>
        </div>
      </div>
      {source.content ? (
        <div className="clause-source-content">
          <MarkdownMessage
            content={source.content}
            shouldHighlightBlock={(text) => highlightedBlocks.has(normalizeText(text))}
          />
        </div>
      ) : null}
    </div>
  );
}

function SectionPath({ value }: { value: unknown }) {
  const parts = sectionPathParts(value);
  if (parts.length === 0) return null;
  return (
    <div className="section-path">
      {parts.map((part, index) => (
        <span key={`${part}-${index}`}>{part}</span>
      ))}
    </div>
  );
}

function sourceReferenceLabel(source: ClauseSource): string {
  const clause = source.clause_no ? ` 条文：${source.clause_no}` : '';
  return `${documentName(source)}${clause}`;
}

function documentName(source: ClauseSource): string {
  return source.clause_name || source.document_name || source.source_id;
}

function sectionPathParts(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.map((item) => textOf(item).trim()).filter(Boolean);
  }
  return textOf(value)
    .split(/\s*[>/／|]\s*|\s{2,}/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function textOf(value: unknown): string {
  if (value === null || value === undefined) return '';
  return typeof value === 'string' ? value : String(value);
}

function buildHighlightedBlocks(answerContent: string, source: ClauseSource): Set<string> {
  const referenceSentence = findReferenceSentence(answerContent, source.source_id);
  const content = source.content ?? '';
  if (!referenceSentence || !content) return new Set();

  const paragraphs = content
    .split(/\n{2,}/)
    .map((item) => item.trim())
    .filter((item) => item && !item.startsWith('#'));
  const scored = paragraphs
    .map((paragraph) => ({
      paragraph,
      score: textSimilarity(referenceSentence, paragraph),
    }))
    .filter((item) => item.score >= 0.08)
    .sort((left, right) => right.score - left.score)
    .slice(0, 2);
  return new Set(scored.map((item) => normalizeText(item.paragraph)));
}

function findReferenceSentence(content: string, sourceId: string): string | null {
  const normalized = content.replace(/\n+/g, ' ');
  const pattern = new RegExp(`[^。！？.!?]*\\[?${escapeRegExp(sourceId)}\\]?[^。！？.!?]*[。！？.!?]?`);
  const match = normalized.match(pattern);
  return match?.[0]?.replace(new RegExp(`\\[?${escapeRegExp(sourceId)}\\]?`, 'g'), '').trim() || null;
}

function textSimilarity(left: string, right: string): number {
  const leftTokens = significantTokens(left);
  const rightTokens = significantTokens(right);
  if (leftTokens.size === 0 || rightTokens.size === 0) return 0;
  let overlap = 0;
  for (const token of leftTokens) {
    if (rightTokens.has(token)) overlap += 1;
  }
  return overlap / Math.sqrt(leftTokens.size * rightTokens.size);
}

function significantTokens(text: string): Set<string> {
  const normalized = normalizeText(text);
  const tokens = new Set<string>();
  for (const match of normalized.matchAll(/[\u4e00-\u9fa5]{2,}|[a-zA-Z0-9]{2,}/g)) {
    const token = match[0].toLowerCase();
    if (!STOP_WORDS.has(token)) tokens.add(token);
  }
  return tokens;
}

function normalizeText(text: string): string {
  return text.replace(/\s+/g, ' ').trim();
}

const STOP_WORDS = new Set([
  '可以',
  '如果',
  '以及',
  '或者',
  '这个',
  '该款',
  '相关',
  '责任',
  '规定',
  '依照',
]);

function normalizeHistoryMessages(messages: ChatMessage[]): ChatMessage[] {
  return messages.map((message) => ({
    role: message.role,
    content: message.content,
    additionalInfo: normalizeAdditionalInfo(message.additional_info),
  }));
}

function isUnauthorized(reason: unknown): boolean {
  return reason instanceof ApiError && reason.status === 401;
}

function formatThreadTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const pad = (num: number) => String(num).padStart(2, '0');
  return `${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}


