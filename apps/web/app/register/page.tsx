import type { Metadata } from 'next';
import { redirect } from 'next/navigation';
import { RegisterForm } from '@/components/RegisterForm';
import { getCurrentUser } from '@/lib/api-server';

export const metadata: Metadata = { title: 'Create account' };

export default async function RegisterPage() {
  const user = await getCurrentUser();
  if (user !== null) {
    redirect('/dashboard');
  }

  return (
    <div className="mx-auto max-w-sm px-4 py-16 sm:py-24">
      <h1 className="m-0 text-2xl font-semibold tracking-tight">Create your account</h1>
      <p className="mt-2 mb-8 text-sm text-muted">Free, local, and yours. No email required.</p>
      <RegisterForm />
    </div>
  );
}
