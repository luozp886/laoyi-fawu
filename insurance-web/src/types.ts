export interface UserSummary {
  id: number;
  username: string;
  email: string;
  displayName: string | null;
}

export interface AuthSession {
  /** 访问令牌（JWT，短时有效，约 2 小时） */
  token: string;
  /** 刷新令牌（长效，约 7 天，用于自动续期） */
  refreshToken: string;
  user: UserSummary;
}

export interface ChatThread {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  additionalInfo?: AdditionalInfo[];
  additional_info?: unknown;
}

export interface ChatHistory {
  thread_id: string;
  messages: ChatMessage[];
  additional_info?: unknown;
}

export interface ClauseSource {
  source_id: string;
  clause_name?: string | null;
  document_name?: string | null;
  section_path?: string | string[] | null;
  clause_no?: string | null;
  content?: string | null;
  score?: number | null;
  [key: string]: unknown;
}

export type AdditionalInfo = {
  type: 'clause_sources';
  sources: ClauseSource[];
};
