import { useEffect, useState } from 'react';

import { AdvisorPage } from './AdvisorPage';
import { logoutAccount, setUnauthorizedHandler } from './api';
import { clearSession, readRefreshToken, readSession, saveSession } from './auth';
import { HomePage } from './HomePage';
import type { AuthSession } from './types';

function navigate(path: string) {
  window.history.pushState({}, '', path);
  window.dispatchEvent(new PopStateEvent('popstate'));
}

export default function App() {
  const [path, setPath] = useState(window.location.pathname);
  const [session, setSession] = useState<AuthSession | null>(() => readSession());

  useEffect(() => {
    const updatePath = () => setPath(window.location.pathname);
    window.addEventListener('popstate', updatePath);
    return () => window.removeEventListener('popstate', updatePath);
  }, []);

  // 全局 401 处理：刷新令牌续期失败时，清空会话并跳转登录页（由 api.ts 触发）
  useEffect(() => {
    setUnauthorizedHandler(() => {
      clearSession();
      setSession(null);
      navigate('/');
    });
    return () => setUnauthorizedHandler(null);
  }, []);

  function authenticated(nextSession: AuthSession) {
    saveSession(nextSession);
    setSession(nextSession);
  }

  function logout() {
    const refreshToken = readRefreshToken();
    if (refreshToken) void logoutAccount(refreshToken);
    clearSession();
    setSession(null);
    if (path !== '/') navigate('/');
  }

  function sessionExpired() {
    clearSession();
    setSession(null);
    navigate('/');
  }

  if (path === '/advisor' && session) {
    return (
      <AdvisorPage
        session={session}
        onBack={() => navigate('/')}
        onSessionExpired={sessionExpired}
      />
    );
  }

  return (
    <HomePage
      session={session}
      initialAuthOpen={path === '/advisor'}
      initialAuthRedirect={() => navigate('/advisor')}
      onAuthenticated={authenticated}
      onLogout={logout}
      onConsult={() => navigate('/advisor')}
    />
  );
}
