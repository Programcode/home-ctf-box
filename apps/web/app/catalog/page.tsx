import type { Metadata } from 'next';
import { Suspense } from 'react';
import { CatalogFilters } from '@/components/CatalogFilters';
import { RoomCard } from '@/components/RoomCard';
import { Skeleton } from '@openrange/ui';
import { catalogFacets, listRooms } from '@/lib/content';

export const metadata: Metadata = { title: 'Catalog' };

export interface CatalogSearchParams {
  difficulty?: string;
  type?: string;
  track?: string;
}

export default async function CatalogPage({
  searchParams,
}: {
  searchParams: Promise<CatalogSearchParams>;
}) {
  const params = await searchParams;
  const rooms = listRooms();
  const facets = catalogFacets();

  const filtered = rooms.filter(
    (room) =>
      (params.difficulty === undefined || room.difficulty === params.difficulty) &&
      (params.type === undefined || room.type === params.type) &&
      (params.track === undefined || room.track === params.track),
  );

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 sm:py-14">
      <header>
        <h1 className="m-0 text-2xl font-semibold tracking-tight sm:text-3xl">Room catalog</h1>
        <p className="mt-2 mb-0 max-w-[60ch] text-sm leading-relaxed text-muted">
          Every room is a versioned content bundle with objectives, scored tasks, and a
          containerized target. {rooms.length} rooms available.
        </p>
      </header>

      <div className="mt-8 rounded-lg border border-edge bg-panel p-4 sm:p-5">
        <Suspense fallback={<Skeleton label="Loading filters" width="100%" height="3rem" />}>
          <CatalogFilters facets={facets} />
        </Suspense>
      </div>

      <p
        aria-live="polite"
        className="mt-6 mb-4 font-mono text-xs uppercase tracking-wide text-muted"
      >
        {filtered.length} of {rooms.length} rooms
      </p>

      {filtered.length === 0 ? (
        <p className="rounded-lg border border-dashed border-edge-strong bg-panel px-5 py-10 text-center text-sm text-muted">
          No rooms match this combination. Clear a filter to widen the search.
        </p>
      ) : (
        <ul className="grid list-none gap-4 p-0 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((room) => (
            <li key={room.slug} className="h-full">
              <RoomCard room={room} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
