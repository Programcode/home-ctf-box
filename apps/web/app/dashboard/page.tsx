import type { Metadata } from 'next';
import Link from 'next/link';
import { redirect } from 'next/navigation';
import { Badge, Card, CardBody, CardHeader, ButtonLink } from '@openrange/ui';
import { getCurrentUser, getServerApiClient } from '@/lib/api-server';
import type { LabInstance } from '@openrange/contracts';

export const metadata: Metadata = { title: 'Dashboard' };
export const dynamic = 'force-dynamic';

const ACTIVE_STATES = new Set(['requested', 'scheduled', 'starting', 'ready', 'resetting']);

export default async function DashboardPage() {
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
  const active = labs.filter((lab) => ACTIVE_STATES.has(lab.state));
  const past = labs.filter((lab) => !ACTIVE_STATES.has(lab.state));

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 sm:py-14">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="m-0 text-2xl font-semibold tracking-tight">
            Welcome back, <span className="font-mono">{user.username}</span>
          </h1>
          <p className="mt-2 mb-0 flex flex-wrap items-center gap-1.5 text-sm text-muted">
            Permissions:
            {user.permissions.map((permission) => (
              <Badge key={permission} className="normal-case">
                {permission}
              </Badge>
            ))}
            {user.permissions.length === 0 ? <span>none</span> : null}
          </p>
        </div>
        <ButtonLink href="/catalog" variant="secondary">
          Find a room
        </ButtonLink>
      </header>

      {apiError !== null ? (
        <p
          role="alert"
          className="mt-8 rounded-md border border-warning bg-panel px-4 py-3 text-sm text-warning"
        >
          {apiError}
        </p>
      ) : null}

      <section aria-labelledby="continue-learning" className="mt-10">
        <h2 id="continue-learning" className="m-0 text-lg font-semibold">
          Continue learning
        </h2>
        {active.length === 0 ? (
          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[0, 1, 2].map((slot) => (
              <Card key={slot} className="border-dashed">
                <CardBody className="pt-5">
                  <p className="m-0 text-sm leading-relaxed">
                    No lab in progress.
                    <br />
                    Pick a room and the range will spin up a private target for you in seconds.
                  </p>
                  <div className="mt-4">
                    <Link
                      href="/catalog"
                      className="font-mono text-sm text-accent underline-offset-4 hover:underline"
                    >
                      Browse catalog →
                    </Link>
                  </div>
                </CardBody>
              </Card>
            ))}
          </div>
        ) : (
          <ul className="mt-4 grid list-none gap-4 p-0 sm:grid-cols-2 lg:grid-cols-3">
            {active.map((lab) => (
              <li key={lab.id}>
                <Card className="h-full">
                  <CardHeader
                    title={lab.room}
                    actions={
                      <Badge variant={lab.state === 'ready' ? 'success' : 'warning'}>
                        {lab.state}
                      </Badge>
                    }
                  />
                  <CardBody>
                    <p className="m-0 font-mono text-xs text-muted">
                      started {new Date(lab.createdAt).toLocaleString()}
                    </p>
                  </CardBody>
                </Card>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="recent-labs" className="mt-12">
        <h2 id="recent-labs" className="m-0 text-lg font-semibold">
          Lab history
        </h2>
        {past.length === 0 ? (
          <p className="mt-3 mb-0 text-sm text-muted">Nothing here yet.</p>
        ) : (
          <ul className="mt-4 grid list-none gap-3 p-0 md:grid-cols-2">
            {past.map((lab) => (
              <li
                key={lab.id}
                className="flex items-center justify-between gap-4 rounded-lg border border-edge bg-panel px-4 py-3"
              >
                <span className="font-medium">{lab.room}</span>
                <span className="flex items-center gap-3">
                  <Badge variant={lab.state === 'failed' ? 'danger' : 'default'}>{lab.state}</Badge>
                  <Link
                    href={`/labs/${lab.id}`}
                    className="font-mono text-sm text-accent underline-offset-4 hover:underline"
                  >
                    open →
                  </Link>
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
