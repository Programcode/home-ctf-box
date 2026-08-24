import type { Metadata } from 'next';
import { ChallengeBoard } from '@/components/ChallengeBoard';

export const metadata: Metadata = { title: 'Challenges' };

export default function ChallengesPage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 sm:py-14">
      <header>
        <h1 className="m-0 text-2xl font-semibold tracking-tight sm:text-3xl">Challenges</h1>
        <p className="mt-2 mb-0 max-w-[60ch] text-sm leading-relaxed text-muted">
          A jeopardy board of standalone puzzles. Points may decay as solves pile up on dynamic
          challenges; submit flags from each challenge's detail view.
        </p>
      </header>
      <ChallengeBoard />
    </div>
  );
}
