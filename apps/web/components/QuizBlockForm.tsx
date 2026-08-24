'use client';

import { useState } from 'react';
import { Button } from '@openrange/ui';
import type { QuizBlockView, QuizAttemptResult } from '@openrange/contracts';
import { apiProxy, ProxyError } from '@/lib/api-browser';

/**
 * Quiz form for one section. Multiple answers per question are allowed (the
 * API grades a sorted id list). Feedback never reveals the answer key; the
 * server only reports per-question correctness.
 */
export function QuizBlockForm({
  moduleSlug,
  sectionId,
  quizzes,
}: {
  moduleSlug: string;
  sectionId: string;
  quizzes: readonly QuizBlockView[];
}) {
  const [selected, setSelected] = useState<Record<string, string[]>>(() =>
    Object.fromEntries(quizzes.map((quiz) => [quiz.question_id, [] as string[]])),
  );
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<QuizAttemptResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  function toggle(questionId: string, optionId: string) {
    setResult(null);
    setError(null);
    setSelected((current) => {
      const chosen = current[questionId] ?? [];
      const next = chosen.includes(optionId)
        ? chosen.filter((id) => id !== optionId)
        : [...chosen, optionId];
      return { ...current, [questionId]: next };
    });
  }

  async function submit() {
    setSubmitting(true);
    setError(null);
    try {
      const attempt = await apiProxy<QuizAttemptResult>(
        `learning/quiz/${encodeURIComponent(sectionId)}/attempt`,
        {
          method: 'POST',
          json: { answers: selected, module: moduleSlug },
        },
      );
      setResult(attempt);
    } catch (caught) {
      setError(caught instanceof ProxyError ? caught.message : 'Could not reach the server.');
    } finally {
      setSubmitting(false);
    }
  }

  const correctness = new Map(
    (result?.results ?? []).map((entry) => [entry.question_id, entry.correct]),
  );

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
    >
      {quizzes.map((quiz) => {
        const verdict = correctness.get(quiz.question_id);
        return (
          <fieldset key={quiz.question_id} className="mt-4 mb-0 rounded-md border border-edge p-3">
            <legend className="px-1 text-sm font-semibold">{quiz.question}</legend>
            <ul className="m-0 list-none p-0">
              {quiz.options.map((option) => {
                const checked = (selected[quiz.question_id] ?? []).includes(option.id);
                return (
                  <li key={option.id}>
                    <label className="flex cursor-pointer items-start gap-2 py-1 text-sm">
                      <input
                        type="checkbox"
                        className="mt-0.5 accent-[var(--or-accent)]"
                        checked={checked}
                        onChange={() => toggle(quiz.question_id, option.id)}
                      />
                      <span>{option.text}</span>
                    </label>
                  </li>
                );
              })}
            </ul>
            {verdict === undefined ? null : (
              <p
                className={[
                  'mb-0 mt-2 text-xs font-medium',
                  verdict ? 'text-accent' : 'text-warning',
                ].join(' ')}
              >
                {verdict ? 'Correct.' : 'Not quite. Review the material and try again.'}
              </p>
            )}
          </fieldset>
        );
      })}

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <Button type="submit" size="sm" disabled={submitting}>
          {submitting ? 'Checking...' : 'Submit answers'}
        </Button>
        <p aria-live="polite" className="mb-0 text-sm">
          {result === null ? null : result.passed ? (
            <span className="font-medium text-accent">All questions correct.</span>
          ) : (
            <span className="text-warning">Some answers are wrong. You can retry.</span>
          )}
          {error !== null ? <span className="text-danger">{error}</span> : null}
        </p>
      </div>
    </form>
  );
}
