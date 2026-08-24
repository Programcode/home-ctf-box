'use client';

import { useState } from 'react';
import { Button, useToast } from '@openrange/ui';
import type { EnrollmentState } from '@openrange/contracts';
import { apiProxy, ProxyError } from '@/lib/api-browser';

type Mutation = 'enroll' | 'pause' | 'resume';

interface EnrollmentResponse {
  readonly path_slug?: string;
  readonly state?: EnrollmentState;
}

const LABELS: Record<Mutation, string> = {
  enroll: 'Enroll',
  pause: 'Pause',
  resume: 'Resume',
};

const PAST_TENSE: Record<Mutation, string> = {
  enroll: 'Enrolled',
  pause: 'Paused',
  resume: 'Resumed',
};

/**
 * Enroll/pause/resume controls for one learning path. The parent owns the
 * displayed state; every successful call reports the new state through
 * `onChange` so both catalog cards and path outlines stay in sync.
 */
export function EnrollmentControls({
  pathSlug,
  state,
  onChange,
}: {
  pathSlug: string;
  state: EnrollmentState | null | undefined;
  onChange: (next: EnrollmentState) => void;
}) {
  const [busy, setBusy] = useState<Mutation | null>(null);
  const toast = useToast();

  const actions: Mutation[] =
    state === 'active'
      ? ['pause']
      : state === 'paused'
        ? ['resume']
        : state === 'completed'
          ? []
          : ['enroll'];

  async function run(mutation: Mutation) {
    setBusy(mutation);
    try {
      const result = await apiProxy<EnrollmentResponse>(
        `learning/paths/${encodeURIComponent(pathSlug)}/${mutation}`,
        { method: 'POST', json: {} },
      );
      if (result.state !== undefined) {
        onChange(result.state);
        toast.push({ title: `${PAST_TENSE[mutation]} in ${pathSlug}`, variant: 'success' });
      }
    } catch (error) {
      toast.push({
        title: `${LABELS[mutation]} failed`,
        description: error instanceof ProxyError ? error.message : 'Could not reach the server.',
        variant: 'error',
      });
    } finally {
      setBusy(null);
    }
  }

  if (actions.length === 0) {
    return null;
  }

  return (
    <span className="inline-flex items-center gap-2">
      {actions.map((mutation) => (
        <Button
          key={mutation}
          size="sm"
          variant={mutation === 'pause' ? 'ghost' : 'primary'}
          disabled={busy !== null}
          onClick={() => void run(mutation)}
        >
          {busy === mutation ? 'Working...' : LABELS[mutation]}
        </Button>
      ))}
    </span>
  );
}
