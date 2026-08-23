'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import type { FormEvent } from 'react';
import { Button, Input } from '@openrange/ui';
import { apiProxy, ProxyError } from '@/lib/api-browser';

interface AuthSessionResponse {
  id: string;
  username: string;
  mfa_pending: boolean;
  csrf_token: string;
}

export function LoginForm() {
  const router = useRouter();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [mfaPending, setMfaPending] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setFormError(null);
    try {
      if (!mfaPending) {
        const session = await apiProxy<AuthSessionResponse>('auth/login', {
          method: 'POST',
          json: { username, password },
        });
        if (session.mfa_pending) {
          setMfaPending(true);
          return;
        }
      } else {
        await apiProxy<{ mfa_pending: boolean }>('auth/mfa/verify', {
          method: 'POST',
          json: { code },
        });
      }
      router.replace('/dashboard');
      router.refresh();
    } catch (error) {
      const message =
        error instanceof ProxyError ? error.message : 'Could not reach the server. Try again.';
      setFormError(message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={(event) => void onSubmit(event)} className="grid gap-5" noValidate>
      {formError !== null ? (
        <p
          role="alert"
          className="m-0 rounded-md border border-danger bg-panel px-3 py-2 text-sm text-danger"
        >
          {formError}
        </p>
      ) : null}
      <Input
        id="login-username"
        label="Username"
        name="username"
        autoComplete="username"
        required
        value={username}
        onChange={(event) => setUsername(event.target.value)}
      />
      <Input
        id="login-password"
        label="Password"
        name="password"
        type="password"
        autoComplete="current-password"
        required
        value={password}
        onChange={(event) => setPassword(event.target.value)}
      />
      {mfaPending ? (
        <Input
          id="login-code"
          label="Two-factor code"
          hint="Six-digit code from your authenticator app, or a recovery code."
          name="code"
          inputMode="text"
          autoComplete="one-time-code"
          required
          value={code}
          onChange={(event) => setCode(event.target.value)}
        />
      ) : null}
      <Button type="submit" size="lg" disabled={busy}>
        {busy ? 'Signing in…' : mfaPending ? 'Verify code' : 'Sign in'}
      </Button>
      <p className="m-0 text-sm text-muted">
        New here?{' '}
        <Link href="/register" className="text-accent underline-offset-4 hover:underline">
          Create an account
        </Link>
      </p>
    </form>
  );
}
