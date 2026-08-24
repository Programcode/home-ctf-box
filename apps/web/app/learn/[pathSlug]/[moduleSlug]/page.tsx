import type { Metadata } from 'next';
import { ModuleReader } from '@/components/ModuleReader';

export const metadata: Metadata = { title: 'Module' };

interface Props {
  params: Promise<{ pathSlug: string; moduleSlug: string }>;
}

export default async function ModulePage({ params }: Props) {
  const { pathSlug, moduleSlug } = await params;
  return (
    <div className="mx-auto max-w-3xl px-4 py-10 sm:px-6 sm:py-14">
      <ModuleReader pathSlug={pathSlug} moduleSlug={moduleSlug} />
    </div>
  );
}
