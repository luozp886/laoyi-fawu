import {
  AuditOutlined,
  CheckCircleOutlined,
  CustomerServiceOutlined,
  FileProtectOutlined,
  FileSearchOutlined,
  InfoCircleOutlined,
  LoginOutlined,
  MessageOutlined,
  RobotOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import { Button } from 'antd';
import { useState } from 'react';

import { AuthModal } from './AuthModal';
import type { AuthSession } from './types';

interface HomePageProps {
  session: AuthSession | null;
  initialAuthOpen?: boolean;
  onAuthenticated: (session: AuthSession) => void;
  onLogout: () => void;
  onConsult: () => void;
  /** 由路径强制登录后的跳转目标（默认走 onConsult 前往咨询页） */
  initialAuthRedirect?: () => void;
}

export function HomePage({
  session,
  initialAuthOpen = false,
  onAuthenticated,
  onLogout,
  onConsult,
  initialAuthRedirect,
}: HomePageProps) {
  const [authOpen, setAuthOpen] = useState(initialAuthOpen);
  const [consultAfterLogin, setConsultAfterLogin] = useState(initialAuthOpen);

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
    if (consultAfterLogin) {
      (initialAuthRedirect ?? onConsult)();
    }
    setConsultAfterLogin(false);
  }

  return (
    <div className="lp">
      <header className="lp-nav">
        <div className="lp-nav__inner">
          <a className="lp-brand" href="#top" aria-label="劳翼法务首页">
            <span className="lp-brand__seal"><FileProtectOutlined /></span>
            <span className="lp-brand__text">
              <strong>劳翼法务</strong>
              <small>劳动法律检索与咨询</small>
            </span>
          </a>
          <nav className="lp-nav__links" aria-label="主导航">
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
                  登录 / 注册
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
            <span className="lp-eyebrow">劳动法规检索 · AI 法律咨询</span>
            <h1 className="lp-hero__title">
              劳动法律问题，
              <br />
              问 AI，附法条依据
            </h1>
            <p className="lp-hero__sub">
              欠薪、被辞退、加班费、工伤、没签合同、仲裁时效……描述你的问题，
              系统检索劳动法规知识库，给你引用真实法条的解答。
            </p>
            <div className="lp-hero__cta">
              <Button type="primary" className="lp-btn-gold lp-btn-lg" icon={<CustomerServiceOutlined />} onClick={consult}>
                免费咨询 · 查法条
              </Button>
              <Button className="lp-btn-outline lp-btn-lg" onClick={() => {
                document.getElementById('how')?.scrollIntoView({ behavior: 'smooth' });
              }}>
                看看怎么用 <CheckCircleOutlined />
              </Button>
            </div>
            <div className="lp-hero__trust">
              <span><CheckCircleOutlined /> 引用法条，可溯源</span>
              <span><CheckCircleOutlined /> 基于法规知识库检索</span>
              <span><CheckCircleOutlined /> 明确免责，仅供参考</span>
            </div>
          </div>

          {/* hero visual: 法规检索结果示例 */}
          <div className="lp-paper" aria-hidden="true">
            <div className="lp-paper__top">
              <span><FileSearchOutlined /> 法规检索结果</span>
              <em>RAG · 6 部劳动法规</em>
            </div>
            <div className="lp-paper__title">《中华人民共和国劳动合同法》</div>
            <div className="lp-paper__sec">第四十七条 · 经济补偿的计算</div>
            <div className="lp-paper__body">
              经济补偿按劳动者在本单位工作的年限，每满一年支付一个月工资的标准向劳动者支付。六个月以上不满一年的，按一年计算；不满六个月的，向劳动者支付半个月工资的经济补偿。
            </div>
            <div className="lp-paper__sec">相关条文</div>
            <div className="lp-paper__body">
              第八十七条 · 违法解除的赔偿金：按经济补偿标准的二倍支付。
            </div>
            <div className="lp-paper__basis">检索来源：劳动合同法 · 劳动争议调解仲裁法 · 社会保险法 等</div>
          </div>
        </div>
      </section>

      {/* ---- How ---- */}
      <section className="lp-section lp-section--soft" id="how">
        <div className="lp-section__head">
          <span className="lp-eyebrow lp-eyebrow--ink">三步开始</span>
          <h2>从提问到拿到依据</h2>
        </div>
        <ol className="lp-steps">
          <li>
            <span className="lp-steps__num">01</span>
            <MessageOutlined />
            <strong>描述问题</strong>
            <p>说出你的劳动法律困惑：欠薪、辞退、加班、工伤、时效……</p>
          </li>
          <li>
            <span className="lp-steps__num">02</span>
            <RobotOutlined />
            <strong>检索法规</strong>
            <p>系统从劳动法规知识库检索相关条文，作为回答依据。</p>
          </li>
          <li>
            <span className="lp-steps__num">03</span>
            <CheckCircleOutlined />
            <strong>获得解答</strong>
            <p>AI 结合法条给出简明解答，条文可点击查看原文。</p>
          </li>
        </ol>
      </section>

      {/* ---- Why ---- */}
      <section className="lp-section" id="why">
        <div className="lp-section__head">
          <span className="lp-eyebrow lp-eyebrow--ink">为什么选择劳翼</span>
          <h2>基于法规检索的智能咨询</h2>
        </div>
        <div className="lp-why">
          <div className="lp-why__item">
            <AuditOutlined />
            <strong>法规知识库检索</strong>
            <span>内置多部劳动法规全文，按语义检索相关条文，不做模型自由发挥。</span>
          </div>
          <div className="lp-why__item">
            <SafetyCertificateOutlined />
            <strong>引用真实法条</strong>
            <span>回答标注条文来源与章节，点击即可查看法条原文。</span>
          </div>
          <div className="lp-why__item">
            <RobotOutlined />
            <strong>多轮对话</strong>
            <span>围绕你的案情持续追问与解答，会话历史自动保存。</span>
          </div>
          <div className="lp-why__item">
            <InfoCircleOutlined />
            <strong>明确免责</strong>
            <span>内容仅供咨询参考，重大涉诉事项建议咨询执业律师。</span>
          </div>
        </div>
      </section>

      <footer className="lp-footer">
        <div className="lp-footer__inner">
          <div className="lp-footer__brand">
            <span className="lp-brand__seal"><FileProtectOutlined /></span>
            <strong>劳翼法务</strong>
          </div>
          <p className="lp-footer__disc">
            劳翼法务提供的内容与解答仅作法律咨询参考，不构成正式法律意见；具体法律后果请以仲裁委、法院及执业律师意见为准。
          </p>
          <nav className="lp-footer__nav">
            <a href="#how">怎么用</a>
            <a href="#why">关于</a>
          </nav>
        </div>
        <div className="lp-footer__bar">© 2026 劳翼法务 · 劳动法规检索与 AI 法律咨询平台</div>
      </footer>

      <AuthModal
        open={authOpen}
        onCancel={() => {
          setAuthOpen(false);
          setConsultAfterLogin(false);
        }}
        onSuccess={authenticated}
      />
    </div>
  );
}



