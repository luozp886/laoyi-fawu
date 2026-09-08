import {
  CustomerServiceOutlined,
  FileProtectOutlined,
  LoginOutlined,
} from '@ant-design/icons';
import { Alert, Button, Empty, Modal, Segmented, Skeleton } from 'antd';
import { useEffect, useState } from 'react';

import { listTemplates } from './api';
import { AuthModal } from './AuthModal';
import { CATEGORY_LABELS } from './categoryLabels';
import { ProductCard } from './ProductCard';
import type { AuthSession, DocumentTemplate, LegalCategory } from './types';

type CategoryFilter = LegalCategory | 'all';

const CATEGORY_OPTIONS: Array<{ label: string; value: CategoryFilter }> = [
  { label: '全部', value: 'all' },
  { label: '劳动仲裁', value: 'arbitration' },
  { label: '解除与补偿', value: 'termination' },
  { label: '工资与加班', value: 'wage' },
  { label: '工伤', value: 'injury' },
  { label: '劳动合同', value: 'contract' },
];

interface HomePageProps {
  session: AuthSession | null;
  initialAuthOpen?: boolean;
  onAuthenticated: (session: AuthSession) => void;
  onLogout: () => void;
  onConsult: () => void;
}

export function HomePage({
  session,
  initialAuthOpen = false,
  onAuthenticated,
  onLogout,
  onConsult,
}: HomePageProps) {
  const [category, setCategory] = useState<CategoryFilter>('all');
  const [templates, setTemplates] = useState<DocumentTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [authOpen, setAuthOpen] = useState(initialAuthOpen);
  const [consultAfterLogin, setConsultAfterLogin] = useState(initialAuthOpen);
  const [selected, setSelected] = useState<DocumentTemplate | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    listTemplates(category, controller.signal)
      .then(setTemplates)
      .catch((reason) => {
        if (reason instanceof DOMException && reason.name === 'AbortError') return;
        setError(reason instanceof Error ? reason.message : '文书加载失败');
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [category, reloadKey]);

  function openAuth(continueToAdvisor = false) {
    setConsultAfterLogin(continueToAdvisor);
    setAuthOpen(true);
  }

  function consult() {
    if (session) {
      onConsult();
      return;
    }
    openAuth(true);
  }

  function authenticated(nextSession: AuthSession) {
    onAuthenticated(nextSession);
    setAuthOpen(false);
    if (consultAfterLogin) onConsult();
    setConsultAfterLogin(false);
  }

  return (
    <div className="page-shell">
      <header className="site-header">
        <div className="site-header__inner">
          <a className="brand" href="/" aria-label="劳翼法务首页">
            <span className="brand__mark"><FileProtectOutlined /></span>
            <span><strong>劳翼法务</strong><small>劳动法律文书与咨询平台</small></span>
          </a>
          <nav className="site-nav" aria-label="主导航">
            <a className="is-active" href="#documents">法律文书</a>
            <a href="#service">服务说明</a>
          </nav>
          <div className="site-actions">
            {session ? (
              <>
                <span className="user-name">{session.user.displayName || session.user.username}</span>
                <Button type="text" onClick={onLogout}>退出</Button>
              </>
            ) : (
              <>
                <Button type="text" icon={<LoginOutlined />} onClick={() => openAuth()}>
                  登录
                </Button>
              </>
            )}
          </div>
        </div>
      </header>

      <main>
        <section className="intro-band">
          <div>
            <h1>把劳动纠纷讲给 AI，按案情生成维权文书</h1>
            <p>覆盖仲裁、解除补偿、工资加班、工伤等常见劳动争议，文书模板仅供参考，重大涉诉事项请咨询执业律师。</p>
          </div>
          <Button type="primary" ghost icon={<CustomerServiceOutlined />} onClick={consult}>
            让顾问帮我分析
          </Button>
        </section>

        <section className="products-section" id="documents">
          <div className="products-heading">
            <div>
              <h2>法律文书</h2>
              <p>根据你的争议类型选择适用的文书</p>
            </div>
            <span>{loading ? '正在加载' : `共 ${templates.length} 份文书`}</span>
          </div>
          <div className="category-filter" aria-label="按纠纷类型筛选">
            <Segmented<CategoryFilter>
              value={category}
              options={CATEGORY_OPTIONS}
              onChange={setCategory}
            />
          </div>

          {error ? (
            <Alert
              className="products-alert"
              type="error"
              showIcon
              message="文书加载失败"
              description={error}
              action={<Button onClick={() => setReloadKey((value) => value + 1)}>重新加载</Button>}
            />
          ) : null}

          {loading ? (
            <div className="product-grid" aria-label="文书加载中">
              {Array.from({ length: 6 }, (_, index) => (
                <div className="product-skeleton" key={index}><Skeleton active /></div>
              ))}
            </div>
          ) : templates.length ? (
            <div className="product-grid">
              {templates.map((template) => (
                <ProductCard key={template.id} template={template} onView={setSelected} />
              ))}
            </div>
          ) : (
            <Empty description="该类型暂时没有可展示的文书" />
          )}
        </section>

        <section className="service-strip" id="service">
          <div><strong>多类文书</strong><span>覆盖常见劳动争议场景</span></div>
          <div><strong>法规支撑</strong><span>回答引用真实法条来源</span></div>
          <div><strong>AI 顾问</strong><span>分析案情、收集要素、生成文书</span></div>
        </section>
      </main>

      <footer className="site-footer">本平台生成与提供的内容仅供模板与参考，不构成正式法律意见，重大涉诉事项请咨询执业律师。</footer>

      <AuthModal
        open={authOpen}
        onCancel={() => {
          setAuthOpen(false);
          setConsultAfterLogin(false);
        }}
        onSuccess={authenticated}
      />

      <Modal
        open={selected !== null}
        title={selected?.name}
        footer={[
          <Button key="close" onClick={() => setSelected(null)}>关闭</Button>,
          <Button key="consult" type="primary" onClick={consult}>咨询顾问生成</Button>,
        ]}
        onCancel={() => setSelected(null)}
        width={620}
      >
        {selected ? (
          <div className="product-detail">
            <p>{selected.description}</p>
            <dl>
              <div><dt>文书类型</dt><dd>{selected.doc_type}</dd></div>
              <div><dt>所属类别</dt><dd>{CATEGORY_LABELS[selected.category]}</dd></div>
              <div><dt>适用场景</dt><dd>{selected.target_scenario}</dd></div>
              <div><dt>依据来源</dt><dd>{selected.source_note}</dd></div>
            </dl>
            {selected.highlights?.length ? (
              <>
                <h4>文书要点</h4>
                <ul>{selected.highlights.map((item) => <li key={item}>{item}</li>)}</ul>
              </>
            ) : null}
            <p className="legal-note">提示：由 AI 顾问根据案情收集要素后结构化生成，仅作模板参考。</p>
          </div>
        ) : null}
      </Modal>
    </div>
  );
}
