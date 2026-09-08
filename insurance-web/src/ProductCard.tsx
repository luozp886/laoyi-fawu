import { RightOutlined } from '@ant-design/icons';
import type { LegalCategory } from './types';
import type { DocumentTemplate } from './types';

export const CATEGORY_META: Record<
  LegalCategory,
  { seal: string; tint: string; ink: string }
> = {
  arbitration: { seal: '裁', tint: '#EAF0FA', ink: '#17324F' },
  termination: { seal: '解', tint: '#F7EEE1', ink: '#8A6A1F' },
  wage: { seal: '薪', tint: '#E8F2EC', ink: '#25614A' },
  injury: { seal: '伤', tint: '#FBECEC', ink: '#A23A3A' },
  contract: { seal: '合', tint: '#EFF1F6', ink: '#3D4B6A' },
};

export function categoryLabel(key: string): string {
  const map: Record<string, string> = {
    arbitration: '劳动仲裁',
    termination: '解除与补偿',
    wage: '工资与加班',
    injury: '工伤',
    contract: '劳动合同',
  };
  return map[key] ?? key;
}

interface DocumentCardProps {
  template: DocumentTemplate;
  onView: (template: DocumentTemplate) => void;
}

export function ProductCard({ template, onView }: DocumentCardProps) {
  const meta = CATEGORY_META[template.category] ?? CATEGORY_META.arbitration;
  return (
    <article className="dd" onClick={() => onView(template)} tabIndex={0} role="button"
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onView(template); }}>
      <header className="dd__top">
        <span className="dd__seal" style={{ background: meta.tint, color: meta.ink }}>
          {meta.seal}
        </span>
        <span className="dd__tag">{categoryLabel(template.category)}</span>
      </header>
      <div className="dd__body">
        <h3 className="dd__name">{template.name}</h3>
        <div className="dd__type">{template.doc_type ?? '法律文书'}</div>
        {template.description ? (
          <p className="dd__desc">{template.description}</p>
        ) : null}
        {template.target_scenario ? (
          <p className="dd__use">适用 · {template.target_scenario}</p>
        ) : null}
      </div>
      <footer className="dd__foot">
        <span className="dd__basis">{template.source_note ?? '依相关劳动法规'}</span>
        <span className="dd__cta">
          查看并生成 <RightOutlined />
        </span>
      </footer>
    </article>
  );
}
