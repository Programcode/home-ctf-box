'use client';

import Link from 'next/link';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Button } from '@openrange/ui';
import type { LabInstance } from '@openrange/contracts';
import { apiProxy, ProxyError } from '@/lib/api-browser';

type Status =
  | { kind: 'idle' }
  | { kind: 'busy'; label: string }
  | { kind: 'open' }
  | { kind: 'closed'; detail: string }
  | { kind: 'error'; detail: string };

interface TerminalTokenResponse {
  readonly token?: string;
}

const CLOSE_CODE_DETAIL: Record<number, string> = {
  1000: 'Session ended.',
  1008: 'Connection refused by policy (bad/expired token or wrong lab).',
  1011: 'Upstream SSH failure.',
  1013: 'Per-lab session limit reached. Close another tab and retry.',
};

/**
 * Browser terminal for one lab instance.
 *
 * Token flow: the gateway verifies short-lived `lab-v1` tokens on
 * `/terminal/{instance_id}?token=...`. The FastAPI endpoint that mints them
 * (`POST /api/labs/{id}/terminal-token`) does not exist yet, so until it
 * ships this page stays gated behind picking a READY lab and surfaces the
 * exact failure instead of pretending to connect. See apps/web/README.md.
 */
export function TerminalClient({ labs }: { labs: readonly LabInstance[] }) {
  const readyLabs = labs.filter((lab) => lab.state === 'ready');
  const [labId, setLabId] = useState<string>('');
  const [status, setStatus] = useState<Status>({ kind: 'idle' });
  const containerRef = useRef<HTMLDivElement>(null);
  const termRef = useRef<{ write: (data: string | Uint8Array) => void } | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const cleanupRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    let disposed = false;
    let observer: ResizeObserver | null = null;

    async function init() {
      const [{ Terminal }, { FitAddon }] = await Promise.all([
        import('@xterm/xterm'),
        import('@xterm/addon-fit'),
      ]);
      if (disposed || containerRef.current === null) {
        return;
      }
      const terminal = new Terminal({
        cursorBlink: true,
        fontFamily: 'var(--or-font-mono), monospace',
        convertEol: true,
      });
      const fit = new FitAddon();
      terminal.loadAddon(fit);
      terminal.open(containerRef.current);
      fit.fit();
      terminal.write('Select a lab and press Connect.\r\n');
      termRef.current = terminal;

      terminal.onData((data) => {
        const socket = socketRef.current;
        if (socket !== null && socket.readyState === WebSocket.OPEN) {
          socket.send(new TextEncoder().encode(data));
        }
      });
      terminal.onResize(({ cols, rows }) => {
        const socket = socketRef.current;
        if (socket !== null && socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({ type: 'resize', cols, rows }));
        }
      });

      observer = new ResizeObserver(() => fit.fit());
      observer.observe(containerRef.current);
      cleanupRef.current = () => {
        observer?.disconnect();
        terminal.dispose();
      };
    }

    void init();
    return () => {
      disposed = true;
      socketRef.current?.close();
      socketRef.current = null;
      cleanupRef.current?.();
    };
  }, []);

  const connect = useCallback(
    async (resume: boolean) => {
      if (labId === '') {
        return;
      }
      socketRef.current?.close();
      socketRef.current = null;

      setStatus({ kind: 'busy', label: resume ? 'Resuming session...' : 'Requesting token...' });
      let token: string;
      try {
        const minted = await apiProxy<TerminalTokenResponse>(
          `labs/${encodeURIComponent(labId)}/terminal-token`,
          { method: 'POST', json: {} },
        );
        if (typeof minted.token !== 'string' || minted.token.length === 0) {
          throw new ProxyError('Token endpoint returned no token.', 500);
        }
        token = minted.token;
      } catch (error) {
        if (error instanceof ProxyError && error.status === 404) {
          setStatus({
            kind: 'error',
            detail:
              'The API does not expose POST /labs/{id}/terminal-token yet, so no gateway token can be minted. This panel connects automatically once the endpoint ships.',
          });
        } else {
          setStatus({
            kind: 'error',
            detail: error instanceof ProxyError ? error.message : 'Could not reach the server.',
          });
        }
        return;
      }

      const base = process.env.NEXT_PUBLIC_GATEWAY_WS_URL ?? 'ws://localhost:8772';
      const params = new URLSearchParams({ token });
      const resumeId = resume ? sessionIdRef.current : null;
      if (resumeId !== null && resume) {
        params.set('resume', resumeId);
      }
      setStatus({ kind: 'busy', label: 'Opening shell...' });

      let socket: WebSocket;
      try {
        socket = new WebSocket(`${base}/terminal/${encodeURIComponent(labId)}?${params}`);
      } catch {
        setStatus({ kind: 'error', detail: `Invalid gateway URL: ${base}` });
        return;
      }
      socket.binaryType = 'arraybuffer';

      socket.onmessage = (event) => {
        if (event.data instanceof ArrayBuffer) {
          termRef.current?.write(new Uint8Array(event.data));
        } else if (typeof event.data === 'string') {
          try {
            const control: unknown = JSON.parse(event.data);
            if (
              control !== null &&
              typeof control === 'object' &&
              control instanceof Object &&
              'session_id' in control &&
              typeof (control as { session_id: unknown }).session_id === 'string'
            ) {
              sessionIdRef.current = (control as { session_id: string }).session_id;
              setStatus({ kind: 'open' });
            }
          } catch {
            // Non-JSON text frames carry no meaning for this client.
          }
        }
      };
      socket.onopen = () => {
        termRef.current?.write('');
        setStatus({ kind: 'open' });
      };
      socket.onclose = (event) => {
        socketRef.current = null;
        setStatus({
          kind: 'closed',
          detail: CLOSE_CODE_DETAIL[event.code] ?? `Connection closed (code ${event.code}).`,
        });
      };
      socket.onerror = () => {
        // onclose always follows; leave messaging to it.
      };
      socketRef.current = socket;
    },
    [labId],
  );

  if (readyLabs.length === 0) {
    return (
      <div className="mt-10 rounded-lg border border-dashed border-edge-strong bg-panel px-5 py-10 text-center">
        <h2 className="m-0 text-lg font-semibold">No running lab</h2>
        <p className="mx-auto mt-2 mb-0 max-w-[52ch] text-sm leading-relaxed text-muted">
          The terminal attaches to a READY lab instance. Start one from any room page, then come
          back here.
        </p>
        <div className="mt-5">
          <Link
            href="/catalog"
            className="font-mono text-sm text-accent underline underline-offset-4 hover:no-underline"
          >
            Browse the catalog
          </Link>
        </div>
      </div>
    );
  }

  const busy = status.kind === 'busy';
  const connected = status.kind === 'open';

  return (
    <div className="mt-6">
      <div className="flex flex-wrap items-end gap-3">
        <div className="flex flex-col gap-1">
          <label htmlFor="terminal-lab" className="text-sm text-muted">
            Lab instance
          </label>
          <select
            id="terminal-lab"
            value={labId}
            onChange={(event) => setLabId(event.target.value)}
            disabled={connected}
            className="rounded-md border border-edge bg-panel px-2 py-1.5 font-mono text-sm"
          >
            <option value="">Select a lab...</option>
            {readyLabs.map((lab) => (
              <option key={lab.id} value={lab.id}>
                {lab.room} ({lab.id.slice(0, 8)})
              </option>
            ))}
          </select>
        </div>
        <Button onClick={() => void connect(false)} disabled={labId === '' || busy || connected}>
          Connect
        </Button>
        <Button
          variant="secondary"
          onClick={() => void connect(true)}
          disabled={labId === '' || busy}
        >
          Reconnect
        </Button>
        {connected ? (
          <Button variant="ghost" onClick={() => socketRef.current?.close()}>
            Disconnect
          </Button>
        ) : null}
      </div>

      <p aria-live="polite" className="mb-2 mt-3 text-sm">
        {status.kind === 'idle' ? (
          <span className="text-muted">Waiting for a connection.</span>
        ) : null}
        {status.kind === 'busy' ? <span className="text-muted">{status.label}</span> : null}
        {status.kind === 'open' ? <span className="text-accent">Connected.</span> : null}
        {status.kind === 'closed' ? (
          <span className="text-warning">Disconnected: {status.detail}</span>
        ) : null}
        {status.kind === 'error' ? (
          <span role="alert" className="text-danger">
            {status.detail}
          </span>
        ) : null}
      </p>

      <div
        role="application"
        aria-label={`Terminal for lab ${labId === '' ? 'none selected' : labId}`}
        className="overflow-hidden rounded-lg border border-edge bg-[#05070a] p-1"
      >
        <div ref={containerRef} className="h-[60vh]" />
      </div>
    </div>
  );
}
