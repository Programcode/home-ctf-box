'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { Badge, Button, Skeleton, useToast } from '@openrange/ui';
import type {
  CalloutTone,
  LearningModule,
  LearningPathDetail,
  ModuleSectionView,
  QuizBlockView,
  SectionBlockView,
} from '@openrange/contracts';
import { apiProxy, isAuthError, ProxyError } from '@/lib/api-browser';
import { Markdown } from './Markdown';
import { QuizBlockForm } from './QuizBlockForm';
import { SignInPrompt } from './SignInPrompt';

type Load =
  | { kind: 'loading' }
  | { kind: 'signedOut' }
  | { kind: 'error'; message: string }
  | { kind: 'ready'; module: LearningModule; detail: LearningPathDetail };

/**
 * Languages offered by the switcher. `en` is the default the API serves;
 * every other candidate must answer 200 on a probe request before the
 * switcher appears at all ("when 200 else hide").
 */
const LANG_CANDIDATES = [{ code: 'hu', label: 'Magyar' }] as const;

function Callout({ tone, markdown }: { tone: CalloutTone; markdown: string }) {
  const border =
    tone === 'danger'
      ? 'border-danger'
      : tone === 'warning'
        ? 'border-warning'
        : tone === 'tip'
          ? 'border-accent'
          : 'border-edge-strong';
  return (
    <aside className={`my-4 rounded-md border-l-4 ${border} bg-raised px-4 py-3`} data-tone={tone}>
      <p className="m-0 font-mono text-[0.7rem] uppercase tracking-wide text-muted">{tone}</p>
      <Markdown>{markdown}</Markdown>
    </aside>
  );
}

function BlockView({ block }: { block: SectionBlockView }) {
  if (block.type === 'prose') {
    return <Markdown>{block.markdown}</Markdown>;
  }
  if (block.type === 'callout') {
    return <Callout tone={block.tone} markdown={block.markdown} />;
  }
  if (block.type === 'code') {
    return (
      <figure className="my-4">
        <figcaption className="font-mono text-[0.7rem] uppercase tracking-wide text-muted">
          {block.language}
        </figcaption>
        <pre className="overflow-x-auto rounded-md border border-edge bg-raised p-3 text-xs leading-relaxed">
          <code className="font-mono">{block.code}</code>
        </pre>
      </figure>
    );
  }
  return null;
}

function MarkCompleteButton({
  moduleSlug,
  section,
  completed,
  onCompleted,
}: {
  moduleSlug: string;
  section: ModuleSectionView;
  completed: boolean;
  onCompleted: (sectionId: string) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  if (completed) {
    return <Badge variant="success">Completed</Badge>;
  }

  async function markComplete() {
    setBusy(true);
    setError(null);
    try {
      await apiProxy(
        `learning/modules/${encodeURIComponent(moduleSlug)}/sections/${encodeURIComponent(section.id)}/complete`,
        { method: 'POST', json: {} },
      );
      onCompleted(section.id);
      toast.push({ title: `Section marked complete`, variant: 'success' });
    } catch (caught) {
      setError(caught instanceof ProxyError ? caught.message : 'Could not reach the server.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <span className="inline-flex flex-col items-end gap-1">
      <Button size="sm" variant="secondary" disabled={busy} onClick={() => void markComplete()}>
        {busy ? 'Saving...' : 'Mark complete'}
      </Button>
      {error !== null ? (
        <span role="alert" className="text-xs text-warning">
          {error}
        </span>
      ) : null}
    </span>
  );
}

export function ModuleReader({ pathSlug, moduleSlug }: { pathSlug: string; moduleSlug: string }) {
  const [load, setLoad] = useState<Load>({ kind: 'loading' });
  const [lang, setLang] = useState('en');
  const [availableLangs, setAvailableLangs] = useState<readonly string[]>([]);

  useEffect(() => {
    let cancelled = false;
    // The switcher only renders when a non-default language actually answers
    // 200 for this module; otherwise it stays hidden entirely.
    async function probe() {
      for (const candidate of LANG_CANDIDATES) {
        try {
          const response = await fetch(
            `/api/or/learning/modules/${encodeURIComponent(moduleSlug)}?lang=${candidate.code}`,
            { credentials: 'same-origin' },
          );
          if (!cancelled && response.ok) {
            setAvailableLangs((current) =>
              current.includes(candidate.code) ? current : [...current, candidate.code],
            );
          }
        } catch {
          // Probe failures keep the switcher hidden.
        }
      }
    }
    void probe();
    return () => {
      cancelled = true;
    };
  }, [moduleSlug]);

  useEffect(() => {
    let cancelled = false;
    const query = lang === 'en' ? '' : `?lang=${encodeURIComponent(lang)}`;
    Promise.all([
      apiProxy<LearningModule>(`learning/modules/${encodeURIComponent(moduleSlug)}${query}`),
      apiProxy<LearningPathDetail>(`learning/paths/${encodeURIComponent(pathSlug)}`),
    ]).then(
      ([moduleBundle, detail]) => {
        if (!cancelled) {
          setLoad({ kind: 'ready', module: moduleBundle, detail });
        }
      },
      (error: unknown) => {
        if (cancelled) {
          return;
        }
        if (isAuthError(error)) {
          setLoad({ kind: 'signedOut' });
        } else if (error instanceof ProxyError && error.status === 404) {
          setLoad({ kind: 'error', message: 'This module does not exist.' });
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
  }, [moduleSlug, pathSlug, lang]);

  const completedSections = useMemo(() => {
    if (load.kind !== 'ready') {
      return new Set<string>();
    }
    return new Set(
      load.detail.modules
        .find((module) => module.slug === moduleSlug)
        ?.sections.filter((section) => section.completed)
        .map((section) => section.id) ?? [],
    );
  }, [load, moduleSlug]);

  function markSectionComplete(sectionId: string) {
    setLoad((current) => {
      if (current.kind !== 'ready') {
        return current;
      }
      return {
        ...current,
        detail: {
          ...current.detail,
          modules: current.detail.modules.map((module) =>
            module.slug !== moduleSlug
              ? module
              : {
                  ...module,
                  sections: module.sections.map((section) =>
                    section.id === sectionId ? { ...section, completed: true } : section,
                  ),
                },
          ),
        },
      };
    });
  }

  if (load.kind === 'loading') {
    return (
      <div className="mt-8 grid gap-4" aria-busy="true">
        <Skeleton label="Loading module" width="100%" height="8rem" />
        <Skeleton label="Loading sections" width="100%" height="24rem" />
      </div>
    );
  }

  if (load.kind === 'signedOut') {
    return <SignInPrompt what="read this module" />;
  }

  if (load.kind === 'error') {
    return (
      <>
        <nav aria-label="Breadcrumb" className="mb-6">
          <Link
            href={`/learn/${pathSlug}`}
            className="font-mono text-sm text-muted hover:text-content"
          >
            ← Back to path
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

  const { module: bundle } = load;
  const canTrackProgress = load.detail.enrollment_state === 'active';

  return (
    <>
      <nav aria-label="Breadcrumb" className="mb-6">
        <Link
          href={`/learn/${pathSlug}`}
          className="font-mono text-sm text-muted hover:text-content"
        >
          ← {load.detail.title}
        </Link>
      </nav>

      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-[60ch]">
          <h1 className="m-0 text-2xl font-semibold tracking-tight">{bundle.title}</h1>
          <p className="mt-2 mb-0 text-sm leading-relaxed text-muted">{bundle.summary}</p>
        </div>
        {availableLangs.length > 0 || lang !== 'en' ? (
          <form className="flex items-center gap-2">
            <label htmlFor="module-lang" className="text-sm text-muted">
              Language
            </label>
            <select
              id="module-lang"
              value={lang}
              onChange={(event) => setLang(event.target.value)}
              className="rounded-md border border-edge bg-panel px-2 py-1.5 text-sm"
            >
              <option value="en">English</option>
              {availableLangs.map((code) => {
                const candidate = LANG_CANDIDATES.find((entry) => entry.code === code);
                return (
                  <option key={code} value={code}>
                    {candidate?.label ?? code}
                  </option>
                );
              })}
            </select>
          </form>
        ) : null}
      </header>

      {bundle.objectives.length > 0 ? (
        <section
          aria-labelledby="objectives-heading"
          className="mt-6 rounded-lg border border-edge bg-panel px-5 py-4"
        >
          <h2
            id="objectives-heading"
            className="m-0 font-mono text-xs uppercase tracking-wide text-muted"
          >
            Objectives
          </h2>
          <ul className="mb-0 mt-2 list-disc pl-5 text-sm leading-relaxed">
            {bundle.objectives.map((objective) => (
              <li key={objective}>{objective}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {bundle.sections.map((section) => (
        <article
          key={section.id}
          id={section.id}
          aria-labelledby={`${section.id}-heading`}
          className="mt-10 scroll-mt-20 rounded-lg border border-edge bg-panel px-5 py-5 sm:px-6"
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 id={`${section.id}-heading`} className="m-0 text-lg font-semibold">
              {section.title}
            </h2>
            {canTrackProgress ? (
              <MarkCompleteButton
                moduleSlug={moduleSlug}
                section={section}
                completed={completedSections.has(section.id)}
                onCompleted={markSectionComplete}
              />
            ) : null}
          </div>

          <div className="mt-3">
            {section.blocks.map((block, index) => {
              if (block.type === 'quiz') {
                const quizzes = section.blocks.filter((b): b is QuizBlockView => b.type === 'quiz');
                if (quizzes[0] !== block) {
                  return null;
                }
                return (
                  <QuizBlockForm
                    key={`quiz-${section.id}`}
                    moduleSlug={moduleSlug}
                    sectionId={section.id}
                    quizzes={quizzes}
                  />
                );
              }
              return <BlockView key={`${block.type}-${index}`} block={block} />;
            })}
          </div>
        </article>
      ))}

      {bundle.cheat_sheet !== null && bundle.cheat_sheet.length > 0 ? (
        <details className="mt-10 rounded-lg border border-edge bg-panel px-5 py-4">
          <summary className="cursor-pointer font-mono text-xs uppercase tracking-wide text-muted">
            Cheat sheet
          </summary>
          <div className="mt-2">
            <Markdown>{bundle.cheat_sheet}</Markdown>
          </div>
        </details>
      ) : null}
    </>
  );
}
