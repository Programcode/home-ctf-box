import type { Metadata } from 'next';
import { redirect } from 'next/navigation';
import { Badge, Card, CardBody, CardHeader } from '@openrange/ui';
import { SessionsTable } from '@/components/SessionsTable';
import { getCurrentUser, getServerApiClient } from '@/lib/api-server';

export const metadata: Metadata = { title: 'Profile' };
export const dynamic = 'force-dynamic';

export default async function ProfilePage() {
  const user = await getCurrentUser();
  if (user === null) {
    redirect('/login');
  }

  let sessions;
  try {
    sessions = [...(await (await getServerApiClient()).users.sessions())];
  } catch {
    sessions = null;
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6 sm:py-14">
      <h1 className="m-0 text-2xl font-semibold tracking-tight">Profile</h1>

      <div className="mt-8 grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader title="Account" actions={<Badge variant="success">active</Badge>} />
          <CardBody>
            <dl className="m-0 grid gap-y-3 text-sm">
              <div>
                <dt className="font-mono text-xs uppercase tracking-wide text-muted">Username</dt>
                <dd className="m-0 font-mono text-content">{user.username}</dd>
              </div>
              <div>
                <dt className="font-mono text-xs uppercase tracking-wide text-muted">
                  Display name
                </dt>
                <dd className="m-0">{user.displayName ?? 'not set'}</dd>
              </div>
              <div>
                <dt className="font-mono text-xs uppercase tracking-wide text-muted">Email</dt>
                <dd className="m-0">
                  {user.email ?? 'none'}{' '}
                  {user.email !== null ? (
                    user.emailVerified ? (
                      <Badge variant="success">verified</Badge>
                    ) : (
                      <Badge variant="warning">unverified</Badge>
                    )
                  ) : null}
                </dd>
              </div>
            </dl>
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Permissions" />
          <CardBody>
            {user.permissions.length === 0 ? (
              <p className="m-0 text-sm text-muted">No permissions assigned.</p>
            ) : (
              <ul className="m-0 flex list-none flex-wrap gap-1.5 p-0">
                {user.permissions.map((permission) => (
                  <li key={permission}>
                    <Badge className="normal-case">{permission}</Badge>
                  </li>
                ))}
              </ul>
            )}
          </CardBody>
        </Card>
      </div>

      <section aria-labelledby="sessions-heading" className="mt-10">
        <h2 id="sessions-heading" className="m-0 text-lg font-semibold">
          Active sessions
        </h2>
        <p className="mt-1 mb-4 text-sm text-muted">
          Every signed-in device gets a session. Revoking one signs that device out immediately.
        </p>
        {sessions === null ? (
          <p
            role="alert"
            className="rounded-md border border-warning bg-panel px-4 py-3 text-sm text-warning"
          >
            Could not load sessions. The API may be unreachable.
          </p>
        ) : (
          <SessionsTable initialSessions={sessions} />
        )}
      </section>
    </div>
  );
}
