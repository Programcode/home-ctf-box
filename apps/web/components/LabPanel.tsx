'use client';

import { useEffect, useMemo, useState } from 'react';
import { Badge, Button, useToast } from '@openrange/ui';
import type { LabDetail, LabInstance, LabState } from '@openrange/contracts';
import { apiProxy, ProxyError } from '@/lib/api-browser';

const STATE_VARIANT: Record<LabState, 'default' | 'success' | 'warning' | 'danger'> = {
  ready: 'success',
  failed: 'danger',
  requested: 'warning',
  scheduled: 'warning',
  starting: 'warning',
  resetting: 'warning',
  stopping: 'warning',
  cleaned: 'default',
  expired: 'default',
};

function formatRemaining(msRemaining: number): string {
  const totalSeconds = Math.max(0, Math.floor(msRemaining / 1000));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const pad = (n: number) => String(n).padStart(2, '0');
  return hours > 0 ? `${hours}:${pad(minutes)}:${pad(seconds)}` : `${pad(minutes)}:${pad(seconds)}`;
}

export function LabPanel({ initial }: { initial: LabDetail }) {
  const [lab, setLab] = useState(initial);
  const [now, setNow] = useState(() => Date.now());
  const [busy, setBusy] = useState<string | null>(null);
  const [armStop, setArmStop] = useState(false);
  const toast = useToast();

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const expiresAtMs = useMemo(
    () => (lab.expiresAt === null ? null : Date.parse(lab.expiresAt)),
    [lab.expiresAt],
  );
  const msRemaining = expiresAtMs === null || Number.isNaN(expiresAtMs) ? null : expiresAtMs - now;

  async function run(action: string, fn: () => Promise<void>) {
    setBusy(action);
    try {
      await fn();
    } catch (error) {
      toast.push({
        title: `${action} failed`,
        description: error instanceof ProxyError ? error.message : 'Could not reach the server.',
        variant: 'error',
      });
    } finally {
      setBusy(null);
    }
  }

  const extend = (minutes: number) =>
    run(`extend +${minutes}m`, async () => {
      const updated = await apiProxy<LabInstance>(`labs/${lab.id}/extend`, {
        method: 'POST',
        json: { minutes },
      });
      setLab({ ...updated, timeRemainingMinutes: 0 });
      setNow(Date.now());
      toast.push({ title: `Extended by ${minutes} minutes`, variant: 'success' });
    });

  const reset = () =>
    run('reset', async () => {
      const updated = await apiProxy<LabInstance>(`labs/${lab.id}/reset`, { method: 'POST' });
      setLab({ ...updated, timeRemainingMinutes: 0 });
      setNow(Date.now());
      toast.push({
        title: 'Target is resetting',
        description: 'The flag changes with the new instance.',
        variant: 'info',
      });
    });

  const stop = () =>
    run('stop', async () => {
      await apiProxy<{ stopped: boolean }>(`labs/${lab.id}`, { method: 'DELETE' });
      toast.push({ title: 'Lab stopped', description: 'The environment was torn down.' });
      window.location.href = '/dashboard';
    });

  const refreshStatus = () =>
    run('refresh', async () => {
      const detail = await apiProxy<LabDetail>(`labs/${lab.id}`);
      setLab(detail);
      setNow(Date.now());
    });

  return (
    <section aria-label="Lab control panel" className="rounded-lg border border-edge bg-panel">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-edge px-5 py-4">
        <div className="flex items-center gap-3">
          <Badge variant={STATE_VARIANT[lab.state]}>{lab.state}</Badge>
          <span className="font-mono text-xs text-muted">{lab.id.slice(0, 8)}</span>
        </div>
        <div className="text-right">
          <p className="m-0 font-mono text-xs uppercase tracking-wide text-muted">Time remaining</p>
          <p className="m-0 font-mono text-2xl font-bold tabular-nums" role="timer" aria-live="off">
            {msRemaining === null ? 'no limit' : formatRemaining(msRemaining)}
          </p>
        </div>
      </div>

      <div className="px-5 py-4">
        <h2 className="m-0 font-mono text-xs uppercase tracking-wide text-muted">Targets</h2>
        {lab.targets.length === 0 ? (
          <p className="mt-2 mb-0 text-sm text-muted">
            No target URLs yet. The runner publishes them once the lab is ready.
          </p>
        ) : (
          <ul className="mt-2 mb-0 grid list-none gap-2 p-0">
            {lab.targets.map((target) => (
              <li key={`${target.name}-${target.url}`} className="font-mono text-sm">
                <span className="mr-2 rounded bg-raised px-1.5 py-0.5 text-xs text-muted">
                  {target.name}
                </span>
                <span className="break-all text-content">{target.url}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2 border-t border-edge px-5 py-4">
        <Button
          variant="secondary"
          size="sm"
          onClick={() => void extend(15)}
          disabled={busy !== null}
        >
          +15 min
        </Button>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => void extend(60)}
          disabled={busy !== null}
        >
          +60 min
        </Button>
        <Button variant="ghost" size="sm" onClick={() => void reset()} disabled={busy !== null}>
          Reset target
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => void refreshStatus()}
          disabled={busy !== null}
        >
          Refresh status
        </Button>
        <span className="ml-auto">
          {armStop ? (
            <span className="inline-flex items-center gap-2">
              <span className="text-xs text-warning">Tear down this lab?</span>
              <Button
                variant="danger"
                size="sm"
                onClick={() => void stop()}
                disabled={busy !== null}
              >
                Confirm stop
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setArmStop(false)}
                disabled={busy !== null}
              >
                Keep it
              </Button>
            </span>
          ) : (
            <Button
              variant="danger"
              size="sm"
              onClick={() => setArmStop(true)}
              disabled={busy !== null}
            >
              Stop lab
            </Button>
          )}
        </span>
      </div>
      <p className="sr-only" aria-live="polite">
        {busy !== null ? `Working: ${busy}` : ''}
      </p>
    </section>
  );
}
