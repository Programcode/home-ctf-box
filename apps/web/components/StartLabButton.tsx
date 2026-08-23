'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { Button, useToast } from '@openrange/ui';
import { apiProxy, ProxyError } from '@/lib/api-browser';

interface LabResponse {
  id: string;
  room: string;
  state: string;
}

export function StartLabButton({
  slug,
  title,
  authenticated,
}: {
  slug: string;
  title: string;
  authenticated: boolean;
}) {
  const router = useRouter();
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!authenticated) {
    return (
      <span className="inline-flex flex-col gap-1">
        <span title="Sign in to start a lab for this room" className="inline-block">
          <Button aria-disabled={true} disabled={true} size="lg">
            Start lab
          </Button>
        </span>
        <span id={`start-lab-hint-${slug}`} className="text-xs text-muted">
          Signing up is free; labs run only for signed-in users.
        </span>
      </span>
    );
  }

  async function start() {
    setBusy(true);
    setError(null);
    try {
      const lab = await apiProxy<LabResponse>('labs', {
        method: 'POST',
        json: { room: slug },
      });
      toast.push({
        title: `Lab starting: ${title}`,
        description: 'The target needs a moment to boot.',
        variant: 'success',
      });
      router.push(`/labs/${lab.id}`);
    } catch (err) {
      if (err instanceof ProxyError && err.status === 403) {
        setError('Your account is missing the lab:start permission.');
      } else if (err instanceof ProxyError && err.status === 409) {
        setError('You already have the maximum number of active labs. Stop one first.');
      } else if (err instanceof ProxyError) {
        setError(err.message);
      } else {
        setError('Could not reach the server. Try again.');
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <span className="inline-flex flex-col gap-1">
      <Button size="lg" onClick={() => void start()} disabled={busy}>
        {busy ? 'Starting…' : 'Start lab'}
      </Button>
      {error !== null ? (
        <span role="alert" className="text-xs text-danger">
          {error}
        </span>
      ) : null}
    </span>
  );
}
