'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { Badge, ButtonLink, Card, CardBody, CardFooter, CardHeader, Skeleton } from '@openrange/ui';
import type { EnrollmentState, LearningPath } from '@openrange/contracts';
import { apiProxy, isAuthError, ProxyError } from '@/lib/api-browser';
import { EnrollmentControls } from './EnrollmentControls';
import { SignInPrompt } from './SignInPrompt';

type Load =
  | { kind: 'loading' }
  | { kind: 'signedOut' }
  | { kind: 'error'; message: string }
  | { kind: 'ready'; paths: LearningPath[] };

const STATE_LABEL: Record<EnrollmentState, string> = {
  active: 'In progress',
  paused: 'Paused',
  completed: 'Completed',
};

const STATE_VARIANT = {
  active: 'success',
  paused: 'warning',
  completed: 'default',
} as const;

export function LearnCatalog() {
  const [load, setLoad] = useState<Load>({ kind: 'loading' });

  useEffect(() => {
    let cancelled = false;
    apiProxy<LearningPath[]>('learning/paths').then(
      (paths) => {
        if (!cancelled) {
          setLoad({ kind: 'ready', paths });
        }
      },
      (error: unknown) => {
        if (cancelled) {
          return;
        }
        if (isAuthError(error)) {
          setLoad({ kind: 'signedOut' });
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
  }, []);

  function setState(slug: string, next: EnrollmentState) {
    setLoad((current) =>
      current.kind === 'ready'
        ? {
            kind: 'ready',
            paths: current.paths.map((path) =>
              path.slug === slug ? { ...path, enrollment_state: next } : path,
            ),
          }
        : current,
    );
  }

  if (load.kind === 'loading') {
    return (
      <div className="mt-8 grid gap-4" aria-busy="true">
        {[0, 1, 2].map((slot) => (
          <Skeleton key={slot} label="Loading learning paths" width="100%" height="9rem" />
        ))}
      </div>
    );
  }

  if (load.kind === 'signedOut') {
    return <SignInPrompt what="browse learning paths" />;
  }

  if (load.kind === 'error') {
    return (
      <p
        role="alert"
        className="mt-8 rounded-md border border-warning bg-panel px-4 py-3 text-sm text-warning"
      >
        {load.message}
      </p>
    );
  }

  return (
    <>
      <p
        aria-live="polite"
        className="mt-6 mb-4 font-mono text-xs uppercase tracking-wide text-muted"
      >
        {load.paths.length} learning {load.paths.length === 1 ? 'path' : 'paths'}
      </p>

      {load.paths.length === 0 ? (
        <p className="rounded-lg border border-dashed border-edge-strong bg-panel px-5 py-10 text-center text-sm text-muted">
          No learning paths are published yet.
        </p>
      ) : (
        <ul className="grid list-none gap-4 p-0 lg:grid-cols-2">
          {load.paths.map((path) => {
            const enrolled = path.enrollment_state !== undefined && path.enrollment_state !== null;
            return (
              <li key={path.slug}>
                <Card className="h-full">
                  <CardHeader
                    title={
                      <Link
                        href={`/learn/${path.slug}`}
                        className="text-content no-underline underline-offset-4 hover:underline"
                      >
                        {path.title}
                      </Link>
                    }
                    actions={
                      enrolled ? (
                        <Badge variant={STATE_VARIANT[path.enrollment_state as EnrollmentState]}>
                          {STATE_LABEL[path.enrollment_state as EnrollmentState]}
                        </Badge>
                      ) : null
                    }
                  />
                  <CardBody>
                    <p className="m-0 text-sm leading-relaxed text-muted">{path.summary}</p>
                    <ul className="mb-0 mt-3 flex list-none flex-wrap gap-2 p-0 font-mono text-xs uppercase tracking-wide text-muted">
                      <li>{path.difficulty}</li>
                      <li aria-hidden="true">·</li>
                      <li>{path.estimated_minutes} min</li>
                      {path.capstones.length > 0 ? (
                        <>
                          <li aria-hidden="true">·</li>
                          <li>capstone room</li>
                        </>
                      ) : null}
                    </ul>
                  </CardBody>
                  <CardFooter className="flex flex-wrap items-center gap-2">
                    <ButtonLink href={`/learn/${path.slug}`} variant="secondary" size="sm">
                      {enrolled ? 'Continue' : 'Outline'}
                    </ButtonLink>
                    <EnrollmentControls
                      pathSlug={path.slug}
                      state={path.enrollment_state}
                      onChange={(next) => setState(path.slug, next)}
                    />
                  </CardFooter>
                </Card>
              </li>
            );
          })}
        </ul>
      )}
    </>
  );
}
