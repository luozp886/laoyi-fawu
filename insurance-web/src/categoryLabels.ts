export const CATEGORY_LABELS: Record<string, string> = {
  arbitration: '劳动仲裁',
  termination: '解除与补偿',
  wage: '工资与加班',
  injury: '工伤',
  contract: '劳动合同',
};

export function formatCategoryLabel(value: unknown): string {
  if (value === null || value === undefined) return '法律文书';
  const key = String(value);
  return CATEGORY_LABELS[key] ?? key;
}
