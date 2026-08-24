'use client';

import { useCallback, useEffect, useState } from 'react';
import { Skeleton } from '@openrange/ui';
import type { ChallengeCategory, ChallengeSummary } from '@openrange/contracts';
import { apiProxy, isAuthError, ProxyError } from '@/lib/api-browser';
import { ChallengeModal } from './ChallengeModal';
import { SignInPrompt } from './SignInPrompt';

type Load =
  | { kind: 'loading' }
  | { kind: 'signedOut' }
  | { kind: 'error'; message: string }
  | { kind: 'ready'; challenges: ChallengeSummary[] };

/** Display order for categories; unknown categories append in API order. */
const CATEGORY_ORDER: readonly ChallengeCategory[] = [
  'web',
  'crypto',
  'pwn',
  'rev',
  'forensics',
  'misc',
  'osint',
];

export function ChallengeBoard() {
  const [load, setLoad] = useState<Load>({ kind: 'loading' });
  const [openSlug, setOpenSlug] = useState<string | null>(null);
  const [solvedSlugs, setSolvedSlugs] = useState<readonly string[]>([]);

  useEffect(() => {
    let cancelled = false;
    apiProxy<ChallengeSummary[]>('challenges').then(
      (challenges) => {
        if (!cancelled) {
          setLoad({ kind: 'ready', challenges });
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

  // Modal callbacks must be stable: the detail loader depends on them.
  const markSolved = useCallback((slug: string) => {
    setSolvedSlugs((current) => (current.includes(slug) ? current : [...current, slug]));
  }, []);

  if (load.kind === 'loading') {
    return (
      <div className="mt-8 grid gap-4 lg:grid-cols-3" aria-busy="true">
        {[0, 1, 2].map((slot) => (
          <Skeleton key={slot} label="Loading challenges" width="100%" height="16rem" />
        ))}
      </div>
    );
  }

  if (load.kind === 'signedOut') {
    return <SignInPrompt what="play challenges" />;
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

  const grouped = new Map<string, ChallengeSummary[]>();
  for (const challenge of load.challenges) {
    const bucket = grouped.get(challenge.category) ?? [];
    bucket.push(challenge);
    grouped.set(challenge.category, bucket);
  }
  const categories = [...grouped.keys()].sort((a, b) => {
    const ia = CATEGORY_ORDER.indexOf(a as ChallengeCategory);
    const ib = CATEGORY_ORDER.indexOf(b as ChallengeCategory);
    return (ia === -1 ? CATEGORY_ORDER.length : ia) - (ib === -1 ? CATEGORY_ORDER.length : ib);
  });

  return (
    <>
      <p
        aria-live="polite"
        className="mt-6 mb-4 font-mono text-xs uppercase tracking-wide text-muted"
      >
        {load.challenges.length} {load.challenges.length === 1 ? 'challenge' : 'challenges'} on the
        board · {solvedSlugs.length} solved by you
      </p>

      {categories.map((category) => {
        const items = grouped.get(category) ?? [];
        return (
          <section key={category} aria-labelledby={`category-${category}`} className="mb-8">
            <h2
              id={`category-${category}`}
              className="m-0 mb-3 font-mono text-sm font-semibold uppercase tracking-widest text-content"
            >
              {category}
              <span className="ml-2 font-normal normal-case tracking-normal text-muted">
                {items.length} {items.length === 1 ? 'challenge' : 'challenges'}
              </span>
            </h2>
            <ul className="grid list-none gap-2 p-0 sm:grid-cols-2 lg:grid-cols-4">
              {items.map((challenge) => {
                const solved = solvedSlugs.includes(challenge.slug);
                return (
                  <li key={challenge.slug}>
                    <button
                      type="button"
                      onClick={() => setOpenSlug(challenge.slug)}
                      aria-label={`${challenge.name}, ${challenge.points} points, ${challenge.solve_count} solves${solved ? ', solved' : ''}`}
                      className={[
                        'flex h-full w-full flex-col items-start gap-1 rounded-lg border px-3 py-3 text-left transition-colors',
                        solved
                          ? 'border-accent/60 bg-panel'
                          : 'border-edge bg-panel hover:border-edge-strong',
                      ].join(' ')}
                    >
                      <span className="w-full break-words text-sm font-medium text-content">
                        {challenge.name}
                      </span>
                      <span className="font-mono text-xs text-muted">
                        {challenge.points} pts · {challenge.solve_count} solves
                      </span>
                      {solved ? (
                        <span className="rounded bg-accent/15 px-1.5 py-0.5 font-mono text-[0.7rem] uppercase tracking-wide text-accent">
                          Solved
                        </span>
                      ) : null}
                    </button>
                  </li>
                );
              })}
            </ul>
          </section>
        );
      })}

      {openSlug !== null ? (
        <ChallengeModal
          key={openSlug}
          slug={openSlug}
          onClose={() => setOpenSlug(null)}
          onSolved={markSolved}
        />
      ) : null}
    </>
  );
}
