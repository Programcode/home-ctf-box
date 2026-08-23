'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';

export function LogoutButton() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  return (
    <button
      type="button"
      disabled={busy}
      onClick={async () => {
        setBusy(true);
        try {
          await fetch('/api/or/auth/logout', { method: 'POST', credentials: 'same-origin' });
          router.push('/');
          router.refresh();
        } finally {
          setBusy(false);
        }
      }}
      className="rounded-md px-2.5 py-1.5 text-sm text-muted hover:text-content disabled:opacity-60"
    >
      Sign out
    </button>
  );
}
