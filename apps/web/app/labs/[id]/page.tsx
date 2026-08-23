import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound, redirect } from 'next/navigation';
import { getCurrentUser, getServerApiClient } from '@/lib/api-server';
import { LabPanel } from '@/components/LabPanel';

export const metadata: Metadata = { title: 'Lab' };
export const dynamic = 'force-dynamic';

interface Props {
  params: Promise<{ id: string }>;
}

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export default async function LabPage({ params }: Props) {
  const { id } = await params;
  if (!UUID_RE.test(id)) {
    notFound();
  }
  const user = await getCurrentUser();
  if (user === null) {
    redirect('/login');
  }

  let lab;
  try {
    lab = await (await getServerApiClient()).labs.get(id);
  } catch {
    // Unknown labs stay hidden: a 404-shaped page for both 404 and 403.
    notFound();
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6 sm:py-14">
      <nav aria-label="Breadcrumb" className="mb-6">
        <Link href="/dashboard" className="font-mono text-sm text-muted hover:text-content">
          ← Dashboard
        </Link>
      </nav>
      <header className="mb-8">
        <h1 className="m-0 text-2xl font-semibold tracking-tight">
          Lab · <span className="font-mono">{lab.room}</span>
        </h1>
        <p className="mt-2 mb-0 text-sm text-muted">
          Started {new Date(lab.createdAt).toLocaleString()}. Everything you do stays inside this
          session's isolated network.
        </p>
      </header>
      <LabPanel initial={lab} />
    </div>
  );
}
