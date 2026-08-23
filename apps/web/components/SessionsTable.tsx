'use client';

import { useState } from 'react';
import { Badge, Table, TableContainer, TBody, TD, TH, THead, TR, useToast } from '@openrange/ui';
import type { UserSessionInfo } from '@openrange/contracts';
import { apiProxy, ProxyError } from '@/lib/api-browser';

function shortUa(userAgent: string): string {
  if (userAgent.length === 0) {
    return 'unknown client';
  }
  const match = userAgent.match(/(Firefox|Edg|Chrome|Safari|Chromium)\/[\d.]+/);
  return match === null ? userAgent.slice(0, 40) : `${match[1] ?? userAgent} · ${match[0]}`;
}

export function SessionsTable({
  initialSessions,
}: {
  initialSessions: readonly UserSessionInfo[];
}) {
  const [sessions, setSessions] = useState(initialSessions);
  const [busyId, setBusyId] = useState<string | null>(null);
  const toast = useToast();

  async function revoke(id: string) {
    setBusyId(id);
    try {
      await apiProxy(`users/me/sessions/${id}`, { method: 'DELETE' });
      setSessions((current) => current.filter((session) => session.id !== id));
      toast.push({ title: 'Session revoked', variant: 'success' });
    } catch (error) {
      toast.push({
        title: 'Revoke failed',
        description: error instanceof ProxyError ? error.message : undefined,
        variant: 'error',
      });
    } finally {
      setBusyId(null);
    }
  }

  if (sessions.length === 0) {
    return <p className="text-sm text-muted">No active sessions.</p>;
  }

  return (
    <TableContainer>
      <Table>
        <THead>
          <TR>
            <TH scope="col">Created</TH>
            <TH scope="col">Client</TH>
            <TH scope="col">Status</TH>
            <TH scope="col">
              <span className="sr-only">Actions</span>
            </TH>
          </TR>
        </THead>
        <TBody>
          {sessions.map((session) => (
            <TR key={session.id}>
              <TD>{new Date(session.createdAt).toLocaleString()}</TD>
              <TD className="max-w-56">
                <span className="block truncate" title={session.userAgent}>
                  {shortUa(session.userAgent)}
                  {session.ipAddress.length > 0 ? (
                    <span className="ml-2 font-mono text-xs text-muted">{session.ipAddress}</span>
                  ) : null}
                </span>
              </TD>
              <TD>
                {session.live ? <Badge variant="success">active</Badge> : <Badge>revoked</Badge>}
              </TD>
              <TD className="text-right">
                <button
                  type="button"
                  onClick={() => void revoke(session.id)}
                  disabled={busyId !== null}
                  className="rounded-md border border-danger px-2.5 py-1 font-mono text-xs text-danger hover:bg-danger/10 disabled:opacity-60"
                >
                  {busyId === session.id ? 'Revoking…' : 'Revoke'}
                </button>
              </TD>
            </TR>
          ))}
        </TBody>
      </Table>
    </TableContainer>
  );
}
