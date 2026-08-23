'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
import { Dialog } from '@openrange/ui';

export function CommandPalette({ authenticated }: { authenticated: boolean }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const router = useRouter();

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setOpen((current) => !current);
      }
    }
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  const logout = useCallback(async () => {
    if (busy) {
      return;
    }
    setBusy(true);
    try {
      await fetch('/api/or/auth/logout', { method: 'POST', credentials: 'same-origin' });
      setOpen(false);
      router.push('/');
      router.refresh();
    } finally {
      setBusy(false);
    }
  }, [busy, router]);

  const actions = [
    { label: 'Browse the catalog', href: '/catalog' },
    { label: 'Go to dashboard', href: '/dashboard' },
    ...(authenticated
      ? [
          { label: 'Open profile and sessions', href: '/profile' },
          { label: 'Sign out', href: undefined },
        ]
      : [{ label: 'Sign in', href: '/login' }]),
  ];

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="hidden rounded-md border border-edge-strong px-2.5 py-1 font-mono text-xs text-muted hover:text-content sm:inline-block"
      >
        <span aria-hidden="true">⌘K</span>
        <span className="sr-only">Open quick actions (Command palette)</span>
      </button>
      <Dialog open={open} onClose={() => setOpen(false)} title="Quick actions">
        <ul className="grid gap-1 list-none p-0 m-0">
          {actions.map((item) =>
            item.href !== undefined ? (
              <li key={item.label}>
                <Link
                  href={item.href}
                  onClick={() => setOpen(false)}
                  className="block rounded-md px-3 py-2 text-content no-underline hover:bg-raised"
                >
                  {item.label}
                </Link>
              </li>
            ) : (
              <li key={item.label}>
                <button
                  type="button"
                  onClick={() => void logout()}
                  disabled={busy}
                  className="block w-full rounded-md px-3 py-2 text-left text-content hover:bg-raised disabled:opacity-60"
                >
                  {item.label}
                </button>
              </li>
            ),
          )}
        </ul>
        <p className="mt-3 font-mono text-xs text-muted">Press Escape to close</p>
      </Dialog>
    </>
  );
}
