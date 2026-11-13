import React from 'react';
import ReactDOM from 'react-dom/client';
import { ConfigProvider } from 'antd';
import 'antd/dist/reset.css';
import App from './App';
import './styles.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: '#14304f',
          colorInfo: '#14304f',
          colorLink: '#b08a34',
          colorLinkHover: '#cba44a',
          colorSuccess: '#25614a',
          colorError: '#a23a3a',
          colorWarning: '#c77700',
          borderRadius: 10,
          fontFamily: 'Inter, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif',
        },
      }}
    >
      <App />
    </ConfigProvider>
  </React.StrictMode>,
);
