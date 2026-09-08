export type LegalCategory = 'arbitration' | 'termination' | 'wage' | 'injury' | 'contract';

export interface DocumentTemplate {
  id: number;
  name: string;
  category: LegalCategory;
  doc_type: string | null;
  source_note: string | null;
  image_url: string | null;
  description: string | null;
  target_scenario: string | null;
  template_key: string;
  element_schema?: Record<string, unknown>;
  highlights: string[];
  status: string;
}

export interface GeneratedDoc {
  id: string;
  template_id: number;
  title: string;
  template_name?: string | null;
  status: string;
  created_at?: string | null;
}

export interface UserSummary {
  id: number;
  username: string;
  email: string;
  displayName: string | null;
}

export interface AuthSession {
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
  interrupt: PlanInterrupt | null;
  additional_info?: unknown;
}

export interface PlanInterrupt {
  plan?: unknown;
  confirm_info: string;
  action: Array<'approve' | 'reject'>;
  /** 文书生成预览（generate_document 中断时会带正文） */
  preview?: string;
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

export interface AdditionalProduct {
  id?: number | string;
  plan_id?: string | null;
  product_id?: number | string;
  name?: string;
  product_name?: string;
  category?: string;
  image_url?: string | null;
  description?: string | null;
  min_premium?: number | string | null;
  annual_premium_budget?: number | string | null;
  target_group?: string | null;
  highlights?: string[];
  recommendation_reason?: string | null;
  reason?: string | null;
  status?: string | null;
  [key: string]: unknown;
}

export interface AdditionalPolicy {
  id?: string;
  policy_number?: string | null;
  application_no?: string | null;
  status?: string | null;
  effective_at?: string | null;
  expires_at?: string | null;
  holder_name?: string | null;
  insured_name?: string | null;
  insured_id_no_masked?: string | null;
  insured_phone?: string | null;
  coverage_amount?: number | string | null;
  premium_amount?: number | string | null;
  payment_frequency?: string | null;
  product_id?: number | string;
  product?: AdditionalProduct;
  coverage_snapshot?: Record<string, unknown> | null;
  policy_snapshot?: Record<string, unknown> | null;
  [key: string]: unknown;
}

export type AdditionalInfo =
  | { type: 'clause_sources'; sources: ClauseSource[] }
  | { type: 'products'; title: string; products: AdditionalProduct[] }
  | { type: 'policies'; title: string; policies: AdditionalPolicy[] };
