import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { Badge, ButtonLink } from '@openrange/ui';
import { StartLabButton } from '@/components/StartLabButton';
import { getCurrentUser } from '@/lib/api-server';
import { getRoom } from '@/lib/content';

interface Props {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const room = getRoom(slug);
  return { title: room === undefined ? 'Room' : `${room.title} · ${room.points} pts` };
}

const DIFFICULTY_VARIANT = new Map<string, 'default' | 'success' | 'warning' | 'danger'>([
  ['beginner', 'default'],
  ['easy', 'success'],
  ['medium', 'warning'],
  ['hard', 'danger'],
  ['insane', 'danger'],
]);

export default async function RoomPage({ params }: Props) {
  const { slug } = await params;
  const room = getRoom(slug);
  if (room === undefined) {
    notFound();
  }

  const user = await getCurrentUser();
  const difficultyVariant = DIFFICULTY_VARIANT.get(room.difficulty) ?? 'default';

  return (
    <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6 sm:py-14">
      <nav aria-label="Breadcrumb" className="mb-6">
        <Link href="/catalog" className="font-mono text-sm text-muted hover:text-content">
          ← Catalog
        </Link>
      </nav>

      <header className="flex flex-wrap items-start justify-between gap-6">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={difficultyVariant}>{room.difficulty}</Badge>
            <Badge>{room.type}</Badge>
            <Badge>{room.track}</Badge>
          </div>
          <h1 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">{room.title}</h1>
          <p className="mt-4 mb-0 max-w-[62ch] leading-relaxed text-muted">{room.summary}</p>
        </div>
        <div className="shrink-0">
          <StartLabButton slug={room.slug} title={room.title} authenticated={user !== null} />
        </div>
      </header>

      <dl className="mt-8 grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-edge bg-edge sm:grid-cols-4">
        <Fact label="Points" value={`${room.points}`} />
        <Fact label="Tasks" value={`${room.tasksCount}`} />
        <Fact label="Est. time" value={`~${room.estimatedMinutes} min`} />
        <Fact label="Version" value={room.version} />
      </dl>

      {room.objectives.length > 0 ? (
        <section aria-labelledby="objectives" className="mt-10">
          <h2 id="objectives" className="m-0 text-lg font-semibold">
            Objectives
          </h2>
          <ul className="mt-4 grid list-none gap-3 p-0">
            {room.objectives.map((objective) => (
              <li
                key={objective}
                className="flex gap-3 rounded-lg border border-edge bg-panel px-4 py-3 leading-relaxed"
              >
                <span aria-hidden="true" className="font-mono text-accent">
                  ▸
                </span>
                {objective}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section
        aria-labelledby="workstation"
        className="mt-10 rounded-lg border border-edge bg-panel p-5"
      >
        <h2 id="workstation" className="m-0 text-sm font-semibold">
          What you need
        </h2>
        <p className="mt-2 mb-0 text-sm leading-relaxed text-muted">
          {room.workstation === 'desktop'
            ? 'A desktop workstation with a browser is provided inside the lab network.'
            : 'A terminal workstation is enough; every target is reachable from your private lab network.'}{' '}
          Nothing you do can leave the lab's isolated containers.
        </p>
      </section>

      {user === null ? (
        <section
          aria-labelledby="signup-callout"
          className="mt-8 flex flex-wrap items-center justify-between gap-4 rounded-lg border border-edge-strong bg-panel px-5 py-4"
        >
          <p className="m-0 text-sm text-muted">
            <span className="font-semibold text-content">Want to try this room?</span> Create a free
            account and start it on your own instance.
          </p>
          <ButtonLink href="/register" size="sm">
            Create account
          </ButtonLink>
        </section>
      ) : null}
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-panel px-4 py-4">
      <dt className="font-mono text-xs uppercase tracking-wide text-muted">{label}</dt>
      <dd className="mt-1 mb-0 font-mono text-xl font-bold text-content">{value}</dd>
    </div>
  );
}
