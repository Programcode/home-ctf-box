import type { Metadata } from 'next';
import { LearnCatalog } from '@/components/LearnCatalog';

export const metadata: Metadata = { title: 'Learn' };

export default function LearnPage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 sm:py-14">
      <header>
        <h1 className="m-0 text-2xl font-semibold tracking-tight sm:text-3xl">Learning paths</h1>
        <p className="mt-2 mb-0 max-w-[60ch] text-sm leading-relaxed text-muted">
          Guided curricula that pair reading, quizzes, and live lab rooms. Enroll to track section
          completion and earn a certificate when the required modules are done.
        </p>
      </header>
      <LearnCatalog />
    </div>
  );
}
