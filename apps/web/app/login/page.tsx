import type { Metadata } from 'next';
import { redirect } from 'next/navigation';
import { LoginForm } from '@/components/LoginForm';
import { getCurrentUser } from '@/lib/api-server';

export const metadata: Metadata = { title: 'Sign in' };

export default async function LoginPage() {
  const user = await getCurrentUser();
  if (user !== null) {
    redirect('/dashboard');
  }

  return (
    <div className="mx-auto max-w-sm px-4 py-16 sm:py-24">
      <h1 className="m-0 text-2xl font-semibold tracking-tight">Sign in</h1>
      <p className="mt-2 mb-8 text-sm text-muted">Welcome back to the range.</p>
      <LoginForm />
    </div>
  );
}
