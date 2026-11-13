import type { AdditionalInfo, ClauseSource } from './types';

/** 后端当前只下发法条来源（clause_sources）附加信息，此处统一做归一化。 */
export function normalizeAdditionalInfo(raw: unknown): AdditionalInfo[] {
  if (!raw) return [];
  if (Array.isArray(raw)) {
    return sourceInfo(raw);
  }
  if (typeof raw !== 'object') return [];

  const record = raw as Record<string, unknown>;
  const wrappedSources = record.clause_sources ?? record.sources;
  if (wrappedSources) {
    return sourceInfo(wrappedSources);
  }
  return sourceInfo(record);
}

function sourceInfo(raw: unknown): AdditionalInfo[] {
  const sources = normalizeSources(raw);
  return sources.length ? [{ type: 'clause_sources', sources }] : [];
}

function normalizeSources(raw: unknown): ClauseSource[] {
  const entries: Array<[string | undefined, unknown]> = Array.isArray(raw)
    ? raw.map((item) => [undefined, item])
    : Object.entries(raw as Record<string, unknown>);
  return entries
    .filter((entry): entry is [string | undefined, Record<string, unknown>] =>
      Boolean(entry[1]) && typeof entry[1] === 'object',
    )
    .map(([sourceId, item]) => ({
      ...item,
      source_id: String(item.source_id ?? sourceId ?? ''),
    }))
    .filter((item) => item.source_id);
}

export function attachInfoToLastAssistantMessage<T extends { role: string; additionalInfo?: AdditionalInfo[] }>(
  messages: T[],
  info: AdditionalInfo[],
): T[] {
  if (info.length === 0) return messages;
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    if (messages[index].role === 'assistant') {
      const next = [...messages];
      next[index] = {
        ...messages[index],
        additionalInfo: [...(messages[index].additionalInfo ?? []), ...info],
      };
      return next;
    }
  }
  return messages;
}
