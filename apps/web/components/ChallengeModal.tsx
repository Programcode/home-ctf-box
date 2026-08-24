'use client';

import { useEffect, useRef, useState } from 'react';
import { Badge, Button, Dialog, useToast } from '@openrange/ui';
import type { ChallengeDetail, FlagSubmitResult } from '@openrange/contracts';
import { apiProxy, ProxyError } from '@/lib/api-browser';
import { Markdown } from './Markdown';

function formatBytes(size: number): string {
  if (size < 1024) {
    return `${size} B`;
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

type Outcome =
  | { kind: 'correct'; points: number | null; firstBlood: boolean; already: boolean }
  | { kind: 'wrong'; message: string }
  | { kind: 'error'; message: string };

/**
 * Detail modal for one challenge: description markdown, attachment downloads,
 * and the flag submit form. Success is celebrated with a toast plus a subtle
 * Solved badge; no confetti.
 */
export function ChallengeModal({
  slug,
  onClose,
  onSolved,
}: {
  slug: string;
  onClose: () => void;
  onSolved: (slug: string) => void;
}) {
  const [detail, setDetail] = useState<ChallengeDetail | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [flag, setFlag] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const flagInputRef = useRef<HTMLInputElement>(null);
  const toast = useToast();

  useEffect(() => {
    let cancelled = false;
    apiProxy<ChallengeDetail>(`challenges/${encodeURIComponent(slug)}`).then(
      (loaded) => {
        if (!cancelled) {
          setDetail(loaded);
          if (loaded.solved_by_me) {
            onSolved(slug);
          }
        }
      },
      (error: unknown) => {
        if (!cancelled) {
          setLoadError(error instanceof ProxyError ? error.message : 'Could not reach the server.');
        }
      },
    );
    return () => {
      cancelled = true;
    };
  }, [slug, onSolved]);

  async function submitFlag(event: React.FormEvent) {
    event.preventDefault();
    if (flag.trim().length === 0) {
      return;
    }
    setSubmitting(true);
    try {
      const result = await apiProxy<FlagSubmitResult>(
        `challenges/${encodeURIComponent(slug)}/submit`,
        { method: 'POST', json: { flag } },
      );
      if (result.correct) {
        setOutcome({
          kind: 'correct',
          points: result.points,
          firstBlood: result.first_blood,
          already: result.already_solved,
        });
        onSolved(slug);
        toast.push({ title: 'Flag accepted', variant: 'success' });
      } else {
        setOutcome({ kind: 'wrong', message: 'That flag is not correct. Try again.' });
        flagInputRef.current?.focus();
        flagInputRef.current?.select();
      }
    } catch (error) {
      const message = error instanceof ProxyError ? error.message : 'Could not reach the server.';
      setOutcome({ kind: 'error', message });
      flagInputRef.current?.focus();
    } finally {
      setSubmitting(false);
    }
  }

  const solved = outcome !== null && outcome.kind === 'correct';
  const outcomeId = 'challenge-outcome';

  return (
    <Dialog open onClose={onClose} title={detail?.name ?? 'Loading challenge'}>
      {detail === null && loadError === null ? (
        <p className="m-0 text-sm text-muted">Loading...</p>
      ) : null}
      {loadError !== null ? (
        <p role="alert" className="m-0 text-sm text-warning">
          {loadError}
        </p>
      ) : null}

      {detail !== null ? (
        <>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={solved || detail.solved_by_me ? 'success' : 'default'}>
              {solved || detail.solved_by_me ? 'Solved' : `${detail.points} pts`}
            </Badge>
            <span className="font-mono text-xs uppercase tracking-wide text-muted">
              {detail.category} · difficulty {detail.difficulty}/10 · {detail.solve_count} solves
            </span>
          </div>

          <div className="mt-4">
            <Markdown>{detail.description}</Markdown>
          </div>

          {detail.files.length > 0 ? (
            <section aria-labelledby="challenge-files" className="mt-4">
              <h3
                id="challenge-files"
                className="m-0 font-mono text-xs uppercase tracking-wide text-muted"
              >
                Files
              </h3>
              <ul className="mb-0 mt-2 list-none p-0">
                {detail.files.map((file) => (
                  <li key={file.id} className="py-1">
                    <a
                      href={`/api/or/challenges/${encodeURIComponent(detail.slug)}/files/${encodeURIComponent(file.id)}`}
                      download={file.filename}
                      className="font-mono text-sm text-accent underline underline-offset-4 hover:no-underline"
                    >
                      {file.filename}
                    </a>
                    <span className="ml-2 font-mono text-xs text-muted">
                      {formatBytes(file.size)}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          {!detail.solved_by_me && !solved ? (
            <form onSubmit={submitFlag} className="mt-5">
              <label htmlFor="challenge-flag" className="or-label">
                Flag
              </label>
              <input
                id="challenge-flag"
                ref={flagInputRef}
                className="or-input font-mono"
                value={flag}
                autoComplete="off"
                spellCheck={false}
                aria-describedby={outcome === null ? undefined : outcomeId}
                onChange={(event) => {
                  setFlag(event.target.value);
                  if (outcome !== null && outcome.kind !== 'correct') {
                    setOutcome(null);
                  }
                }}
              />
              <div className="mt-3 flex flex-wrap items-center gap-3">
                <Button type="submit" disabled={submitting || flag.trim().length === 0}>
                  {submitting ? 'Submitting...' : 'Submit flag'}
                </Button>
              </div>
            </form>
          ) : null}

          <p id={outcomeId} aria-live="polite" className="mb-0 mt-3 text-sm">
            {outcome === null ? null : outcome.kind === 'correct' ? (
              <span className="inline-flex flex-wrap items-center gap-2 text-accent">
                <span>
                  {outcome.already
                    ? 'Already solved earlier.'
                    : outcome.points !== null
                      ? `+${outcome.points} points awarded.`
                      : 'Correct.'}
                </span>
                {outcome.firstBlood ? (
                  <span className="font-mono text-xs uppercase tracking-wide">
                    First blood on this challenge.
                  </span>
                ) : null}
              </span>
            ) : (
              <span
                role="alert"
                className={outcome.kind === 'wrong' ? 'text-warning' : 'text-danger'}
              >
                {outcome.message}
              </span>
            )}
          </p>
        </>
      ) : null}
    </Dialog>
  );
}
