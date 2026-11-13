import {
  clearSession,
  readAccessToken,
  readRefreshToken,
  updateTokens,
} from './auth';
import type {
  AuthSession,
  ChatHistory,
  ChatThread,
} from './types';

export const API_BASE = '/api/v1';

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

type UnauthorizedHandler = () => void;
let unauthorizedHandler: UnauthorizedHandler | null = null;

/**
 * 注册全局 401 处理器（App 启动时调用）：清空本地会话并跳转登录页。
 * 当刷新令牌也失效、无法续期时触发，实现“让前端跳转登录页面”。
 */
export function setUnauthorizedHandler(handler: UnauthorizedHandler | null): void {
  unauthorizedHandler = handler;
}

function notifyUnauthorized(): void {
  clearSession();
  unauthorizedHandler?.();
}

interface AuthPayload {
  token: string;
  refresh_token: string;
  user: { id: number; username: string; email: string; display_name?: string | null };
}

/** 后端登录/注册/刷新响应（snake_case）→ 前端 AuthSession（camelCase） */
function toAuthSession(data: AuthPayload): AuthSession {
  return {
    token: data.token,
    refreshToken: data.refresh_token,
    user: {
      id: data.user.id,
      username: data.user.username,
      email: data.user.email,
      displayName: data.user.display_name ?? data.user.username,
    },
  };
}

let refreshing: Promise<boolean> | null = null;

/** 用刷新令牌换取新的访问令牌（双 token 自动续期），并轮换刷新令牌 */
async function tryRefresh(): Promise<boolean> {
  const refreshToken = readRefreshToken();
  if (!refreshToken) return false;
  if (!refreshing) {
    refreshing = (async () => {
      try {
        const response = await fetch(`${API_BASE}/auth/refresh`, {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (!response.ok) return false;
        const data = (await response.json()) as AuthPayload;
        updateTokens(data.token, data.refresh_token);
        return true;
      } catch {
        return false;
      } finally {
        refreshing = null;
      }
    })();
  }
  return refreshing;
}

async function parseError(response: Response): Promise<ApiError> {
  const error = await response.json().catch(() => null);
  return new ApiError(error?.detail ?? error?.message ?? '请求失败，请稍后重试', response.status);
}

interface RequestOptions {
  /** 跳过鉴权头（登录/注册/刷新/登出等白名单接口） */
  skipAuth?: boolean;
}

/**
 * 统一请求封装：自动携带 Authorization: Bearer <accessToken>；
 * 遇 401 时先用刷新令牌自动续期并重试，续期失败则通知跳转登录页。
 */
async function request<T>(
  path: string,
  init?: RequestInit,
  options?: RequestOptions,
): Promise<T> {
  const isForm = init?.body instanceof FormData;

  const doFetch = async (): Promise<Response> => {
    const headers: Record<string, string> = {
      ...(init?.headers as Record<string, string> | undefined),
    };
    if (!isForm) headers['Content-Type'] = 'application/json';
    const token = readAccessToken();
    if (token && !options?.skipAuth) headers['Authorization'] = `Bearer ${token}`;
    return fetch(`${API_BASE}${path}`, {
      ...init,
      credentials: 'include',
      headers,
    });
  };

  let response = await doFetch();
  if (response.status === 401 && !options?.skipAuth) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      response = await doFetch();
    } else {
      notifyUnauthorized();
    }
  }

  if (!response.ok) throw await parseError(response);
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

/** 账号登录 */
export function loginAccount(username: string, password: string): Promise<AuthSession> {
  return request<AuthPayload>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  }, { skipAuth: true }).then(toAuthSession);
}

/** 注册账号 */
export function registerAccount(input: {
  username: string;
  email: string;
  password: string;
  displayName?: string;
}): Promise<AuthSession> {
  return request<AuthPayload>('/auth/register', {
    method: 'POST',
    body: JSON.stringify({
      username: input.username,
      email: input.email,
      password: input.password,
      display_name: input.displayName || undefined,
    }),
  }, { skipAuth: true }).then(toAuthSession);
}

/** 退出登录（撤销服务端刷新令牌；本地会话由调用方清理） */
export async function logoutAccount(refreshToken: string): Promise<void> {
  try {
    await request<void>('/auth/logout', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
    }, { skipAuth: true });
  } catch {
    // 服务端撤销失败不阻塞前端退出
  }
}

// ==================== 咨询会话 ====================

export function listChatThreads(): Promise<ChatThread[]> {
  return request<ChatThread[]>('/chat-threads');
}

export function createChatThread(title = '法律咨询'): Promise<ChatThread> {
  return request<ChatThread>('/chat-threads', {
    method: 'POST',
    body: JSON.stringify({ title }),
  });
}

export function getChatHistory(threadId: string): Promise<ChatHistory> {
  return request<ChatHistory>(`/chat-threads/${threadId}/messages`);
}

export function renameChatThread(threadId: string, title: string): Promise<ChatThread> {
  return request<ChatThread>(`/chat-threads/${threadId}`, {
    method: 'PATCH',
    body: JSON.stringify({ title }),
  });
}

export async function deleteChatThread(threadId: string): Promise<void> {
  await request<void>(`/chat-threads/${threadId}`, {
    method: 'DELETE',
  });
}

export async function streamChat(
  threadId: string,
  input: { message?: string },
  handlers: {
    onMessage: (chunk: string) => void;
    onAdditionalInfo?: (info: unknown) => void;
  },
): Promise<void> {
  const doFetch = async (): Promise<Response> => {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    const token = readAccessToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
    return fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ thread_id: threadId, ...input }),
    });
  };

  let response = await doFetch();
  if (response.status === 401) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      response = await doFetch();
    } else {
      notifyUnauthorized();
      throw new ApiError('登录已失效，请重新登录', 401);
    }
  }

  if (!response.ok || !response.body) {
    throw await parseError(response);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split(/\r?\n\r?\n/);
    buffer = parts.pop() ?? '';
    parts.forEach((eventText) => handleSseEvent(eventText, handlers));
  }
  if (buffer.trim()) {
    handleSseEvent(buffer, handlers);
  }
}

function handleSseEvent(
  eventText: string,
  handlers: {
    onMessage: (chunk: string) => void;
    onAdditionalInfo?: (info: unknown) => void;
  },
) {
  const lines = eventText.split(/\r?\n/);
  const event = lines.find((line) => line.startsWith('event:'))?.slice(6).trim();
  const data = lines
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.slice(5).trimStart())
    .join('\n');
  if (!data) return;
  if (event === 'message') {
    handlers.onMessage(parseSseMessage(data));
    return;
  }
  if (event === 'additional_info') {
    handlers.onAdditionalInfo?.(parseJsonLike(data) ?? data);
  }
}

function parseSseMessage(data: string): string {
  try {
    const value = JSON.parse(data) as unknown;
    return typeof value === 'string' ? value : JSON.stringify(value);
  } catch {
    return data;
  }
}

function parseJsonLike(data: string): unknown {
  try {
    return JSON.parse(data);
  } catch {
    return null;
  }
}
