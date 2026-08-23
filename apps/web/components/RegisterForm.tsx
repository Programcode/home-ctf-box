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
}

export function RegisterForm() {
  const router = useRouter();
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [usernameError, setUsernameError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    setUsernameError(null);
    setPasswordError(null);
    setBusy(true);
    try {
      await apiProxy<AuthSessionResponse>('auth/register', {
        method: 'POST',
        json: {
          username,
          password,
          ...(email.trim().length > 0 ? { email: email.trim() } : {}),
        },
      });
      router.replace('/dashboard');
      router.refresh();
    } catch (error) {
      if (error instanceof ProxyError) {
        if (error.status === 422 && /password/i.test(error.message)) {
          setPasswordError(error.message);
        } else if (error.status === 422 || /username/i.test(error.message)) {
          setUsernameError(error.message);
        } else {
          setFormError(error.message);
        }
      } else {
        setFormError('Could not reach the server. Try again.');
      }
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
        id="register-username"
        label="Username"
        name="username"
        autoComplete="username"
        required
        hint="Letters and digits, up to 32 characters."
        error={usernameError ?? undefined}
        value={username}
        onChange={(event) => setUsername(event.target.value)}
      />
      <Input
        id="register-email"
        label="Email"
        name="email"
        type="email"
        autoComplete="email"
        hint="Optional; used for password recovery only."
        value={email}
        onChange={(event) => setEmail(event.target.value)}
      />
      <Input
        id="register-password"
        label="Password"
        name="password"
        type="password"
        autoComplete="new-password"
        required
        hint="At least 12 characters. A passphrase works well."
        error={passwordError ?? undefined}
        value={password}
        onChange={(event) => setPassword(event.target.value)}
      />
      <Button type="submit" size="lg" disabled={busy}>
        {busy ? 'Creating account…' : 'Create account'}
      </Button>
      <p className="m-0 text-sm text-muted">
        Already registered?{' '}
        <Link href="/login" className="text-accent underline-offset-4 hover:underline">
          Sign in
        </Link>
      </p>
    </form>
  );
}
