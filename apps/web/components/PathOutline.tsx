'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { Badge, ButtonLink, Card, CardBody, Skeleton } from '@openrange/ui';
import type { EnrollmentState, LearningPathDetail, PathSectionRef } from '@openrange/contracts';
import { apiProxy, isAuthError, ProxyError } from '@/lib/api-browser';
import { EnrollmentControls } from './EnrollmentControls';
import { SignInPrompt } from './SignInPrompt';

type Load =
  | { kind: 'loading' }
  | { kind: 'signedOut' }
  | { kind: 'error'; message: string }
  | { kind: 'ready'; detail: LearningPathDetail };

function SectionRow({
  pathSlug,
  moduleSlug,
  section,
  enrolled,
}: {
  pathSlug: string;
  moduleSlug: string;
  section: PathSectionRef;
  enrolled: boolean;
}) {
  const href = `/learn/${pathSlug}/${moduleSlug}#${section.id}`;
  return (
    <li className="flex flex-wrap items-center gap-x-3 gap-y-1 py-1.5">
      <Link
        href={href}
        className="text-sm text-content underline-offset-4 hover:underline"
        aria-label={`Open section ${section.title}${section.completed ? ' (completed)' : ''}`}
      >
        {section.title}
      </Link>
      <span
        className={[
          'rounded px-1.5 py-0.5 font-mono text-[0.7rem] uppercase tracking-wide',
          section.completed ? 'bg-accent/15 text-accent' : 'bg-raised text-muted',
        ].join(' ')}
      >
        {section.completed ? 'Completed' : 'Not started'}
      </span>
      {section.optional_branch ? (
        <span className="font-mono text-[0.7rem] uppercase tracking-wide text-muted">optional</span>
      ) : null}
      {!enrolled || section.completed ? null : (
        <span className="basis-full pl-0 text-xs text-muted sm:basis-auto">
          {section.prerequisites.length > 0
            ? `Requires ${section.prerequisites.map((p) => `${p.module}/${p.section}`).join(', ')}`
            : 'No prerequisites'}
        </span>
      )}
    </li>
  );
}

export function PathOutline({ pathSlug }: { pathSlug: string }) {
  const [load, setLoad] = useState<Load>({ kind: 'loading' });

  useEffect(() => {
    let cancelled = false;
    apiProxy<LearningPathDetail>(`learning/paths/${encodeURIComponent(pathSlug)}`).then(
      (detail) => {
        if (!cancelled) {
          setLoad({ kind: 'ready', detail });
        }
      },
      (error: unknown) => {
        if (cancelled) {
          return;
        }
        if (isAuthError(error)) {
          setLoad({ kind: 'signedOut' });
        } else if (error instanceof ProxyError && error.status === 404) {
          setLoad({ kind: 'error', message: 'This learning path does not exist.' });
        } else {
          setLoad({
            kind: 'error',
            message: error instanceof ProxyError ? error.message : 'Could not reach the server.',
          });
        }
      },
    );
    return () => {
      cancelled = true;
    };
  }, [pathSlug]);

  const setState = (next: EnrollmentState) => {
    setLoad((current) =>
      current.kind === 'ready'
        ? { kind: 'ready', detail: { ...current.detail, enrollment_state: next } }
        : current,
    );
  };

  if (load.kind === 'loading') {
    return (
      <div className="mt-8 grid gap-4" aria-busy="true">
        <Skeleton label="Loading path outline" width="100%" height="12rem" />
        <Skeleton label="Loading modules" width="100%" height="18rem" />
      </div>
    );
  }

  if (load.kind === 'signedOut') {
    return <SignInPrompt what="open this path" />;
  }

  if (load.kind === 'error') {
    return (
      <>
        <nav aria-label="Breadcrumb" className="mb-6">
          <Link href="/learn" className="font-mono text-sm text-muted hover:text-content">
            ← Learning paths
          </Link>
        </nav>
        <p
          role="alert"
          className="mt-8 rounded-md border border-warning bg-panel px-4 py-3 text-sm text-warning"
        >
          {load.message}
        </p>
      </>
    );
  }

  const { detail } = load;
  const enrolled = detail.enrollment_state === 'active' || detail.enrollment_state === 'paused';
  const totalSections = detail.modules.reduce(
    (sum, module) => sum + module.sections.filter((s) => !s.optional_branch).length,
    0,
  );
  const doneSections = detail.modules.reduce(
    (sum, module) => sum + module.sections.filter((s) => s.completed && !s.optional_branch).length,
    0,
  );

  return (
    <>
      <nav aria-label="Breadcrumb" className="mb-6">
        <Link href="/learn" className="font-mono text-sm text-muted hover:text-content">
          ← Learning paths
        </Link>
      </nav>

      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-[60ch]">
          <h1 className="m-0 text-2xl font-semibold tracking-tight">{detail.title}</h1>
          <p className="mt-2 mb-0 text-sm leading-relaxed text-muted">{detail.summary}</p>
          <ul className="mb-0 mt-3 flex list-none flex-wrap items-center gap-2 p-0 font-mono text-xs uppercase tracking-wide text-muted">
            <li>{detail.difficulty}</li>
            <li aria-hidden="true">·</li>
            <li>{detail.estimated_minutes} min</li>
            <li aria-hidden="true">·</li>
            <li>
              {doneSections}/{totalSections} required sections complete
            </li>
          </ul>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {detail.enrollment_state !== undefined && detail.enrollment_state !== null ? (
            <Badge variant={detail.enrollment_state === 'active' ? 'success' : 'default'}>
              {detail.enrollment_state}
            </Badge>
          ) : null}
          <EnrollmentControls
            pathSlug={detail.slug}
            state={detail.enrollment_state}
            onChange={setState}
          />
        </div>
      </header>

      <ol className="mb-0 mt-8 grid list-none gap-4 p-0">
        {detail.modules.map((module, index) => (
          <li key={module.slug}>
            <Card>
              <CardBody>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h2 className="m-0 text-base font-semibold">
                    <span className="mr-2 font-mono text-sm text-muted">
                      {String(index + 1).padStart(2, '0')}
                    </span>
                    <Link
                      href={`/learn/${pathSlug}/${module.slug}`}
                      className="text-content no-underline underline-offset-4 hover:underline"
                    >
                      {module.title}
                    </Link>
                  </h2>
                  {module.optional_branch ? (
                    <Badge>optional branch</Badge>
                  ) : (
                    <ButtonLink
                      href={`/learn/${pathSlug}/${module.slug}`}
                      variant="secondary"
                      size="sm"
                    >
                      Open module
                    </ButtonLink>
                  )}
                </div>
                <ul className="mb-0 mt-2 list-none divide-y divide-edge p-0">
                  {module.sections.map((section) => (
                    <SectionRow
                      key={`${module.slug}-${section.id}`}
                      pathSlug={pathSlug}
                      moduleSlug={module.slug}
                      section={section}
                      enrolled={enrolled}
                    />
                  ))}
                </ul>
              </CardBody>
            </Card>
          </li>
        ))}
      </ol>
    </>
  );
}
