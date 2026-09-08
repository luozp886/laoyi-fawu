import { useEffect, useState } from 'react';

import { AdvisorPage } from './AdvisorPage';
import { clearSession, readSession, saveSession } from './auth';
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

  function authenticated(nextSession: AuthSession) {
    saveSession(nextSession);
    setSession(nextSession);
  }

  function logout() {
    clearSession();
    setSession(null);
    if (path === '/advisor') navigate('/');
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
        onApplyProduct={() => { /* 法律平台由顾问在对话内完成文书生成，无独立投保页 */ }}
      />
    );
  }

  return (
    <HomePage
      session={session}
      initialAuthOpen={path === '/advisor'}
      onAuthenticated={authenticated}
      onLogout={logout}
      onConsult={() => navigate('/advisor')}
    />
  );
}
