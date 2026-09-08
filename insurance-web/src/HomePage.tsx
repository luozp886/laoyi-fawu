import {
  ArrowRightOutlined,
  AuditOutlined,
  CheckCircleOutlined,
  CustomerServiceOutlined,
  FileProtectOutlined,
  FileTextOutlined,
  InfoCircleOutlined,
  LoginOutlined,
  RobotOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import { Alert, Button, Empty, Modal, Segmented, Skeleton } from 'antd';
import { useEffect, useState } from 'react';

import { listTemplates } from './api';
import { AuthModal } from './AuthModal';
import { CATEGORY_META, categoryLabel, ProductCard } from './ProductCard';
import type { AuthSession, DocumentTemplate, LegalCategory } from './types';

type CategoryFilter = LegalCategory | 'all';
const CATEGORY_ORDER: LegalCategory[] = ['arbitration', 'termination', 'wage', 'injury', 'contract'];

const CATEGORY_HINT: Record<LegalCategory, string> = {
  arbitration: '劳动仲裁 · 应诉答辩',
  termination: '被迫解除 · 经济补偿',
  wage: '欠薪 · 加班费 · 二倍工资',
  injury: '工伤认定 · 工伤待遇',
  contract: '劳动合同范本 · 必备条款',
};

const CATEGORY_OPTIONS: Array<{ label: string; value: CategoryFilter }> = [
  { label: '全部', value: 'all' },
  ...CATEGORY_ORDER.map((c) => ({ label: categoryLabel(c), value: c as CategoryFilter })),
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

  // 类别卡片上的数量：仅在“全部”时可得
  const countOf = (key: LegalCategory) => templates.filter((t) => t.category === key).length;

  function consult() {
    if (session) {
      onConsult();
      return;
    }
    setConsultAfterLogin(true);
    setAuthOpen(true);
  }

  function authenticated(nextSession: AuthSession) {
    onAuthenticated(nextSession);
    setAuthOpen(false);
    if (consultAfterLogin) onConsult();
    setConsultAfterLogin(false);
  }

  function pickCategory(value: CategoryFilter, scroll = false) {
    setCategory(value);
    if (scroll) {
      document.getElementById('documents')?.scrollIntoView({ behavior: 'smooth' });
    }
  }

  return (
    <div className="lp">
      <header className="lp-nav">
        <div className="lp-nav__inner">
          <a className="lp-brand" href="#top" aria-label="劳翼法务首页">
            <span className="lp-brand__seal"><FileProtectOutlined /></span>
            <span className="lp-brand__text">
              <strong>劳翼法务</strong>
              <small>劳动法律文书与咨询</small>
            </span>
          </a>
          <nav className="lp-nav__links" aria-label="主导航">
            <a href="#categories">选文书</a>
            <a href="#documents">文书库</a>
            <a href="#how">怎么用</a>
            <a href="#why">关于</a>
          </nav>
          <div className="lp-nav__actions">
            {session ? (
              <>
                <span className="lp-user">{session.user.displayName || session.user.username}</span>
                <Button onClick={onLogout} className="lp-btn-ghost">退出</Button>
              </>
            ) : (
              <>
                <Button type="primary" className="lp-btn-gold" icon={<CustomerServiceOutlined />} onClick={consult}>
                  免费咨询
                </Button>
                <Button className="lp-btn-ghost" icon={<LoginOutlined />} onClick={() => setAuthOpen(true)}>
                  登录
                </Button>
              </>
            )}
          </div>
        </div>
      </header>

      {/* ---- Hero ---- */}
      <section className="lp-hero" id="top">
        <div className="lp-hero__inner">
          <div className="lp-hero__copy">
            <span className="lp-eyebrow">劳动权益 · AI 智能文书</span>
            <h1 className="lp-hero__title">
              把纠纷讲清楚，
              <br />
              AI 帮你写成维权文书
            </h1>
            <p className="lp-hero__sub">
              欠薪、被辞退、加班费、工伤、没签合同……向顾问描述你的遭遇，
              它会判断案情、引用真实法条，并为你起草可用的法律文书。
            </p>
            <div className="lp-hero__cta">
              <Button type="primary" className="lp-btn-gold lp-btn-lg" icon={<CustomerServiceOutlined />} onClick={consult}>
                免费咨询 · 生成文书
              </Button>
              <Button className="lp-btn-outline lp-btn-lg" onClick={() => pickCategory('all', true)}>
                先浏览文书 <ArrowRightOutlined />
              </Button>
            </div>
            <div className="lp-hero__trust">
              <span><CheckCircleOutlined /> 引用法条，可溯源</span>
              <span><CheckCircleOutlined /> 结构化起草，不编造</span>
              <span><CheckCircleOutlined /> 明确免责，仅供参考</span>
            </div>
          </div>

          {/* hero visual: sample arbitration application */}
          <div className="lp-paper" aria-hidden="true">
            <div className="lp-paper__top">
              <span>劳动人事争议仲裁委员会</span>
              <em>申请号：LA-2026-0001</em>
            </div>
            <div className="lp-paper__title">劳动仲裁申请书</div>
            <dl className="lp-paper__row">
              <div><dt>申请人</dt><dd>张三（劳动者）</dd></div>
              <div><dt>被申请人</dt><dd>××科技有限公司</dd></div>
            </dl>
            <div className="lp-paper__sec">一、仲裁请求</div>
            <div className="lp-paper__body">
              1. 裁决被申请人支付拖欠工资 ¥15,000<br />
              2. 裁决被申请人支付经济补偿 ¥20,000
            </div>
            <div className="lp-paper__sec">二、事实与理由</div>
            <div className="lp-paper__body">
              申请人于 2021 年入职，被申请人自 2026 年 3 月起未足额支付劳动报酬……
            </div>
            <div className="lp-paper__basis">依据《劳动争议调解仲裁法》第二条、第五条</div>
          </div>
        </div>
      </section>

      {/* ---- Category entry ---- */}
      <section className="lp-section" id="categories">
        <div className="lp-section__head">
          <span className="lp-eyebrow lp-eyebrow--ink">按你的情况</span>
          <h2>先选出适用的文书类型</h2>
        </div>
        <div className="lp-cats">
          {CATEGORY_ORDER.map((key) => {
            const meta = CATEGORY_META[key];
            return (
              <button
                key={key}
                className="lp-cat"
                onClick={() => pickCategory(key, true)}
              >
                <span className="lp-cat__seal" style={{ background: meta.tint, color: meta.ink }}>
                  {meta.seal}
                </span>
                <span className="lp-cat__text">
                  <strong>{categoryLabel(key)}</strong>
                  <small>{CATEGORY_HINT[key]}</small>
                  <em>{category === 'all' ? `${countOf(key)} 份文书` : '查看 →'}</em>
                </span>
              </button>
            );
          })}
        </div>
      </section>

      {/* ---- Documents ---- */}
      <section className="lp-section lp-section--soft" id="documents">
        <div className="lp-section__head lp-section__head--row">
          <div>
            <span className="lp-eyebrow lp-eyebrow--ink">文书库</span>
            <h2>法律文书模板</h2>
          </div>
          <span className="lp-count">{loading ? '加载中' : `共 ${templates.length} 份`}</span>
        </div>
        <div className="lp-filter">
          <Segmented<CategoryFilter> value={category} options={CATEGORY_OPTIONS} onChange={setCategory} />
        </div>

        {error ? (
          <Alert
            className="lp-alert"
            type="error"
            showIcon
            message="文书加载失败"
            description={error}
            action={<Button onClick={() => setReloadKey((v) => v + 1)}>重新加载</Button>}
          />
        ) : null}

        {loading ? (
          <div className="dd-grid">
            {Array.from({ length: 6 }, (_, i) => (
              <div className="dd dd--skel" key={i}><Skeleton active /></div>
            ))}
          </div>
        ) : templates.length ? (
          <div className="dd-grid">
            {templates.map((t) => (
              <ProductCard key={t.id} template={t} onView={setSelected} />
            ))}
          </div>
        ) : (
          <Empty description="该类型暂无文书，换个类型看看，或直接咨询顾问" />
        )}
      </section>

      {/* ---- Why ---- */}
      <section className="lp-section" id="why">
        <div className="lp-section__head">
          <span className="lp-eyebrow lp-eyebrow--ink">为什么选择劳翼</span>
          <h2>不只是聊天，而是能落到文书上</h2>
        </div>
        <div className="lp-why">
          <div className="lp-why__item">
            <SafetyCertificateOutlined />
            <strong>覆盖常见争议</strong>
            <span>仲裁、解除补偿、工资加班、工伤、合同，五类场景文书齐全。</span>
          </div>
          <div className="lp-why__item">
            <AuditOutlined />
            <strong>引用真实法条</strong>
            <span>回答与文书依据来自劳动法规检索结果，标注来源、可溯源。</span>
          </div>
          <div className="lp-why__item">
            <RobotOutlined />
            <strong>结构化起草</strong>
            <span>按模板收集要素后受控拼装，不做模型自由发挥，降低编造风险。</span>
          </div>
          <div className="lp-why__item">
            <InfoCircleOutlined />
            <strong>明确免责</strong>
            <span>内容仅供模板参考，重大涉诉事项建议咨询执业律师。</span>
          </div>
        </div>
      </section>

      {/* ---- How ---- */}
      <section className="lp-section lp-section--soft" id="how">
        <div className="lp-section__head">
          <span className="lp-eyebrow lp-eyebrow--ink">三步开始</span>
          <h2>从一句话到一份文书</h2>
        </div>
        <ol className="lp-steps">
          <li>
            <span className="lp-steps__num">01</span>
            <FileTextOutlined />
            <strong>讲清纠纷</strong>
            <p>把遭遇说给顾问：欠薪、辞退、加班、工伤……</p>
          </li>
          <li>
            <span className="lp-steps__num">02</span>
            <RobotOutlined />
            <strong>顾问定方案</strong>
            <p>AI 判断类型、引法条、给维权方案，并向你补齐要素。</p>
          </li>
          <li>
            <span className="lp-steps__num">03</span>
            <CheckCircleOutlined />
            <strong>生成并下载</strong>
            <p>结构化起草《仲裁申请书》等文书，核对后可下载。</p>
          </li>
        </ol>
      </section>

      <footer className="lp-footer">
        <div className="lp-footer__inner">
          <div className="lp-footer__brand">
            <span className="lp-brand__seal"><FileProtectOutlined /></span>
            <strong>劳翼法务</strong>
          </div>
          <p className="lp-footer__disc">
            劳翼法务提供的内容与文书仅作模板与参考，不构成正式法律意见；具体法律后果请以仲裁委、法院及执业律师意见为准。
          </p>
          <nav className="lp-footer__nav">
            <a href="#documents">文书库</a>
            <a href="#how">怎么用</a>
            <a href="#why">关于</a>
          </nav>
        </div>
        <div className="lp-footer__bar">© 2026 劳翼法务 · 劳动法律智能文书与咨询平台</div>
      </footer>

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
          <Button key="consult" type="primary" onClick={consult} icon={<CustomerServiceOutlined />}>
            找顾问生成
          </Button>,
        ]}
        onCancel={() => setSelected(null)}
        width={640}
      >
        {selected ? (
          <div className="lp-modal">
            <p>{selected.description}</p>
            <dl>
              <div><dt>文书类型</dt><dd>{selected.doc_type ?? '—'}</dd></div>
              <div><dt>所属类别</dt><dd>{categoryLabel(selected.category)}</dd></div>
              <div><dt>适用场景</dt><dd>{selected.target_scenario ?? '—'}</dd></div>
              <div><dt>依据来源</dt><dd>{selected.source_note ?? '依相关劳动法规'}</dd></div>
            </dl>
            {selected.highlights?.length ? (
              <>
                <h4>文书要点</h4>
                <ul>{selected.highlights.map((h) => <li key={h}>{h}</li>)}</ul>
              </>
            ) : null}
          </div>
        ) : null}
      </Modal>
    </div>
  );
}
