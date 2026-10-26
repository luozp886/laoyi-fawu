import {
  LockOutlined,
  MailOutlined,
  SafetyCertificateOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { Alert, Form, Input, Modal, Tabs } from 'antd';
import { useState } from 'react';

import { loginAccount, registerAccount } from './api';
import type { AuthSession } from './types';

interface AuthModalProps {
  open: boolean;
  onCancel: () => void;
  onSuccess: (session: AuthSession) => void;
}

interface LoginValues {
  username: string;
  password: string;
}

interface RegisterValues {
  username: string;
  email: string;
  displayName?: string;
  password: string;
  confirm: string;
}

export function AuthModal({ open, onCancel, onSuccess }: AuthModalProps) {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(action: () => Promise<AuthSession>) {
    setLoading(true);
    setError(null);
    try {
      onSuccess(await action());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '操作失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  }

  function handleLogin(values: LoginValues) {
    void run(() => loginAccount(values.username.trim(), values.password));
  }

  function handleRegister(values: RegisterValues) {
    void run(() =>
      registerAccount({
        username: values.username.trim(),
        email: values.email.trim(),
        password: values.password,
        displayName: values.displayName?.trim() || undefined,
      }),
    );
  }

  return (
    <Modal
      open={open}
      title={null}
      footer={null}
      width={440}
      onCancel={onCancel}
      destroyOnHidden
      centered
    >
      <div className="auth-modal__header">
        <span
          className="auth-modal__seal"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: 44,
            height: 44,
            borderRadius: 12,
            background: 'linear-gradient(135deg, #2f6fed, #5b8cff)',
            color: '#fff',
            fontSize: 22,
            marginBottom: 10,
          }}
        >
          <SafetyCertificateOutlined />
        </span>
        <h2>欢迎来到劳翼法务</h2>
        <p>注册 / 登录后即可使用 AI 咨询与文书生成</p>
      </div>
      {error ? (
        <Alert type="error" message={error} showIcon style={{ marginBottom: 16 }} />
      ) : null}
      <Tabs
        activeKey={mode}
        onChange={(key) => {
          setMode(key as 'login' | 'register');
          setError(null);
        }}
        centered
        items={[
          {
            key: 'login',
            label: '登录',
            children: (
              <Form<LoginValues>
                layout="vertical"
                onFinish={handleLogin}
                requiredMark={false}
                size="large"
              >
                <Form.Item
                  label="用户名"
                  name="username"
                  rules={[{ required: true, message: '请输入用户名' }]}
                >
                  <Input
                    prefix={<UserOutlined />}
                    placeholder="用户名（演示账号：骆智鹏）"
                    autoComplete="username"
                  />
                </Form.Item>
                <Form.Item
                  label="密码"
                  name="password"
                  rules={[{ required: true, message: '请输入密码' }]}
                >
                  <Input.Password
                    prefix={<LockOutlined />}
                    placeholder="请输入密码（演示账号：123456）"
                    autoComplete="current-password"
                  />
                </Form.Item>
                <button className="auth-submit" type="submit" disabled={loading}>
                  {loading ? '登录中…' : '登 录'}
                </button>
              </Form>
            ),
          },
          {
            key: 'register',
            label: '注册',
            children: (
              <Form<RegisterValues>
                layout="vertical"
                onFinish={handleRegister}
                requiredMark={false}
                size="large"
              >
                <Form.Item
                  label="用户名"
                  name="username"
                  rules={[
                    { required: true, message: '请输入用户名' },
                    { min: 2, max: 80, message: '用户名 2-80 个字符' },
                  ]}
                >
                  <Input prefix={<UserOutlined />} placeholder="设置用户名" autoComplete="username" />
                </Form.Item>
                <Form.Item
                  label="邮箱"
                  name="email"
                  rules={[
                    { required: true, message: '请输入邮箱' },
                    { type: 'email', message: '邮箱格式不正确' },
                  ]}
                >
                  <Input prefix={<MailOutlined />} placeholder="用于找回账号（如 123@qq.com）" />
                </Form.Item>
                <Form.Item
                  label="昵称（选填）"
                  name="displayName"
                  rules={[{ max: 100, message: '昵称过长' }]}
                >
                  <Input placeholder="不填则默认使用用户名" />
                </Form.Item>
                <Form.Item
                  label="密码"
                  name="password"
                  rules={[
                    { required: true, message: '请设置密码' },
                    { min: 6, max: 64, message: '密码至少 6 位' },
                  ]}
                >
                  <Input.Password
                    prefix={<LockOutlined />}
                    placeholder="至少 6 位"
                    autoComplete="new-password"
                  />
                </Form.Item>
                <Form.Item
                  label="确认密码"
                  name="confirm"
                  dependencies={['password']}
                  rules={[
                    { required: true, message: '请再次输入密码' },
                    ({ getFieldValue }) => ({
                      validator(_, value) {
                        if (!value || getFieldValue('password') === value) {
                          return Promise.resolve();
                        }
                        return Promise.reject(new Error('两次输入的密码不一致'));
                      },
                    }),
                  ]}
                >
                  <Input.Password
                    prefix={<LockOutlined />}
                    placeholder="再次输入密码"
                    autoComplete="new-password"
                  />
                </Form.Item>
                <button className="auth-submit" type="submit" disabled={loading}>
                  {loading ? '注册中…' : '注册并登录'}
                </button>
              </Form>
            ),
          },
        ]}
      />
    </Modal>
  );
}
