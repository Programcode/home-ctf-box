import Link from 'next/link';
import { ButtonLink } from '@openrange/ui';
import { listRooms } from '@/lib/content';

export default function LandingPage() {
  const rooms = listRooms();
  const totalPoints = rooms.reduce((sum, room) => sum + room.points, 0);
  const guided = rooms.filter((room) => room.type === 'guided').length;

  return (
    <div className="mx-auto max-w-6xl px-4 sm:px-6">
      <section className="grid gap-10 py-16 sm:py-24 md:grid-cols-12 md:items-end">
        <div className="md:col-span-7">
          <p className="m-0 font-mono text-xs uppercase tracking-[0.18em] text-accent">
            Self-hosted cyber range
          </p>
          <h1 className="mt-4 text-4xl font-bold leading-[1.05] tracking-tight text-content sm:text-5xl lg:text-6xl">
            Learn to break things
            <br />
            on hardware you own.
          </h1>
          <p className="mt-5 max-w-[52ch] text-lg leading-relaxed text-muted">
            OpenRange runs vulnerable labs in isolated Docker containers on your machine or VPS.
            Solve challenges, capture flags, learn the exploit.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-4">
            <ButtonLink href="/catalog" size="lg">
              Browse rooms
            </ButtonLink>
            <ButtonLink
              href="https://github.com/Programcode/home-ctf-box"
              variant="secondary"
              size="lg"
              rel="noreferrer noopener"
              target="_blank"
            >
              View source
            </ButtonLink>
          </div>
        </div>
        <dl className="grid grid-cols-3 gap-px overflow-hidden rounded-lg border border-edge bg-edge md:col-span-5">
          <Stat label="Rooms" value={String(rooms.length)} />
          <Stat label="Guided" value={String(guided)} />
          <Stat label="Points" value={String(totalPoints)} />
        </dl>
      </section>

      <section aria-labelledby="how-it-works" className="border-t border-edge py-16">
        <h2 id="how-it-works" className="m-0 text-2xl font-semibold tracking-tight">
          How a session goes
        </h2>
        <ol className="mt-8 grid list-none gap-6 p-0 md:grid-cols-3">
          {[
            {
              title: 'Pick a room',
              body: 'Each room is a declarative bundle: objectives, tasks, scoring, and a containerized target with a healthcheck.',
            },
            {
              title: 'Get a private lab',
              body: 'The orchestrator builds an isolated network for your session only. Default-deny egress keeps everything contained.',
            },
            {
              title: 'Capture the flag',
              body: 'Every session gets its own flag. Submit what you find, read the walkthrough, move up the track.',
            },
          ].map((step, index) => (
            <li key={step.title} className="rounded-lg border border-edge bg-panel p-6">
              <span className="font-mono text-xs text-accent">0{index + 1}</span>
              <h3 className="mb-2 mt-3 text-base font-semibold">{step.title}</h3>
              <p className="m-0 text-sm leading-relaxed text-muted">{step.body}</p>
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="self-host" className="border-t border-edge py-16">
        <div className="grid gap-10 md:grid-cols-12">
          <div className="md:col-span-5">
            <h2 id="self-host" className="m-0 text-2xl font-semibold tracking-tight">
              Your range, your rules
            </h2>
          </div>
          <div className="md:col-span-7">
            <p className="m-0 max-w-[60ch] leading-relaxed text-muted">
              No accounts on someone else&apos;s server, no telemetry, no subscription. The stack is
              FastAPI, Postgres, Redis, and a lab-runner that speaks an HMAC-signed contract to
              Docker. Clone the repo, run{' '}
              <code className="rounded bg-raised px-1.5 py-0.5 font-mono text-sm text-content">
                make up
              </code>
              , and the whole platform lives behind your own domain.
            </p>
            <p className="mt-4 mb-0 max-w-[60ch] leading-relaxed text-muted">
              AGPL-3.0 code, CC BY-SA 4.0 content. If you improve either, share it back.
            </p>
          </div>
        </div>
      </section>

      <section aria-labelledby="start-here" className="border-t border-edge py-16 pb-24">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 id="start-here" className="m-0 text-2xl font-semibold tracking-tight">
              Start somewhere small
            </h2>
            <p className="mt-2 mb-0 text-muted">
              Beginner rooms walk you through the tooling before the challenge rooms assume it.
            </p>
          </div>
          <Link
            href="/catalog"
            className="font-mono text-sm text-accent underline-offset-4 hover:underline"
          >
            All {rooms.length} rooms →
          </Link>
        </div>
        <ul className="mt-8 grid list-none gap-4 p-0 sm:grid-cols-2 lg:grid-cols-3">
          {rooms.slice(0, 3).map((room) => (
            <li key={room.slug} className="rounded-lg border border-edge bg-panel p-5">
              <Link
                href={`/catalog/${room.slug}`}
                className="font-semibold text-content no-underline hover:text-accent"
              >
                {room.title}
              </Link>
              <p className="mt-2 mb-0 flex flex-wrap gap-x-3 gap-y-1 font-mono text-xs text-muted">
                <span>{room.difficulty}</span>
                <span>{room.points} pts</span>
                <span>~{room.estimatedMinutes} min</span>
              </p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col-reverse bg-panel px-4 py-5 text-center">
      <dt className="mt-1 font-mono text-xs uppercase tracking-wide text-muted">{label}</dt>
      <dd className="m-0 font-mono text-2xl font-bold text-content">{value}</dd>
    </div>
  );
}
