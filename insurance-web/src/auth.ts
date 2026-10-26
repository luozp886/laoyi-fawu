import type { AuthSession } from './types';

const STORAGE_KEY = 'labor-law-auth-v3';

export function readSession(): AuthSession | null {
  try {
    const value = window.localStorage.getItem(STORAGE_KEY);
    return value ? (JSON.parse(value) as AuthSession) : null;
  } catch {
    window.localStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

export function saveSession(session: AuthSession): void {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
}

export function clearSession(): void {
  window.localStorage.removeItem(STORAGE_KEY);
}

/** 读取访问令牌（JWT） */
export function readAccessToken(): string | null {
  return readSession()?.token ?? null;
}

/** 读取刷新令牌（双 token 机制） */
export function readRefreshToken(): string | null {
  return readSession()?.refreshToken ?? null;
}

/** 刷新成功后更新本地保存的两个令牌 */
export function updateTokens(accessToken: string, refreshToken: string): void {
  const session = readSession();
  if (!session) return;
  saveSession({ ...session, token: accessToken, refreshToken });
}
