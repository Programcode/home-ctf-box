import type { Metadata } from 'next';
import { PathOutline } from '@/components/PathOutline';

export const metadata: Metadata = { title: 'Learning path' };

interface Props {
  params: Promise<{ pathSlug: string }>;
}

export default async function LearningPathPage({ params }: Props) {
  const { pathSlug } = await params;
  return (
    <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6 sm:py-14">
      <PathOutline pathSlug={pathSlug} />
    </div>
  );
}
