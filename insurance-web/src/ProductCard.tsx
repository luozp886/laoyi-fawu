import { CheckCircleOutlined, RightOutlined, FileTextOutlined } from '@ant-design/icons';
import { Button } from 'antd';

import { CATEGORY_LABELS } from './categoryLabels';
import type { DocumentTemplate } from './types';

interface DocumentCardProps {
  template: DocumentTemplate;
  onView: (template: DocumentTemplate) => void;
}

export function ProductCard({ template, onView }: DocumentCardProps) {
  return (
    <article className="product-card">
      <div className="product-card__main">
        <div className="product-card__media">
          <span><FileTextOutlined /></span>
          <strong>{CATEGORY_LABELS[template.category]}</strong>
        </div>
        <div className="product-card__summary">
          <h3 title={template.name}>{template.name}</h3>
          <p className="product-card__insurer">{template.doc_type ?? '法律文书'}</p>
          <p className="product-card__description">{template.description}</p>
        </div>
      </div>
      <div className="product-card__audience">
        <FileTextOutlined />
        <span>适用：{template.target_scenario ?? '未说明'}</span>
      </div>
      <ul className="product-card__highlights">
        {(template.highlights ?? []).slice(0, 3).map((highlight) => (
          <li key={highlight}>
            <CheckCircleOutlined />
            <span>{highlight}</span>
          </li>
        ))}
      </ul>
      <div className="product-card__footer">
        <div>
          <span>依据</span>
          <strong className="product-card__source">{template.source_note ?? '—'}</strong>
        </div>
        <Button type="link" onClick={() => onView(template)}>
          查看详情 <RightOutlined />
        </Button>
      </div>
    </article>
  );
}
