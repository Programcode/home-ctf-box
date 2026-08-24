import type { Metadata } from 'next';
import Link from 'next/link';
import { redirect } from 'next/navigation';
import { getCurrentUser, getServerApiClient } from '@/lib/api-server';
import type { LabInstance } from '@openrange/contracts';
import { TerminalClient } from '@/components/TerminalClient';

export const metadata: Metadata = { title: 'Terminal' };
export const dynamic = 'force-dynamic';

export default async function TerminalPage() {
  const user = await getCurrentUser();
  if (user === null) {
    redirect('/login');
  }

  let labs: LabInstance[] = [];
  let apiError: string | null = null;
  try {
    labs = [...(await (await getServerApiClient()).labs.list())];
  } catch {
    apiError = 'Could not load your labs. Is the API server running?';
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 sm:py-14">
      <header>
        <h1 className="m-0 text-2xl font-semibold tracking-tight sm:text-3xl">Terminal</h1>
        <p className="mt-2 mb-0 max-w-[60ch] text-sm leading-relaxed text-muted">
          An SSH shell into one of your lab instances, bridged through the gateway. Pick a READY
          lab; every keystroke stays inside that isolated session.
        </p>
      </header>

      {apiError !== null ? (
        <p
          role="alert"
          className="mt-8 rounded-md border border-warning bg-panel px-4 py-3 text-sm text-warning"
        >
          {apiError}
        </p>
      ) : (
        <TerminalClient labs={labs} />
      )}

      <p className="mb-0 mt-6 text-xs leading-relaxed text-muted">
        Need a target first?{' '}
        <Link href="/catalog" className="text-accent underline underline-offset-4">
          Start a lab
        </Link>{' '}
        from any room page.
      </p>
    </div>
  );
}
