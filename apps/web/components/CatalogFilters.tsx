'use client';

import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useCallback } from 'react';

export interface Facets {
  difficulties: string[];
  types: string[];
  tracks: string[];
}

const GROUPS: Array<{ key: string; label: string; values: (facets: Facets) => string[] }> = [
  { key: 'difficulty', label: 'Difficulty', values: (f) => f.difficulties },
  { key: 'type', label: 'Type', values: (f) => f.types },
  { key: 'track', label: 'Track', values: (f) => f.tracks },
];

/**
 * Catalog filters. Each toggle writes a single query parameter
 * (`?difficulty=easy&type=guided`), so filtered views are shareable URLs.
 * The grid itself is rendered server-side from those same params.
 */
export function CatalogFilters({ facets }: { facets: Facets }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const toggle = useCallback(
    (key: string, value: string) => {
      const params = new URLSearchParams(searchParams.toString());
      if (params.get(key) === value) {
        params.delete(key);
      } else {
        params.set(key, value);
      }
      const query = params.toString();
      router.replace(query.length > 0 ? `${pathname}?${query}` : pathname, { scroll: false });
    },
    [pathname, router, searchParams],
  );

  return (
    <form
      role="search"
      aria-label="Filter rooms"
      onSubmit={(event) => event.preventDefault()}
      className="grid gap-4 sm:grid-cols-3"
    >
      {GROUPS.map((group) => (
        <fieldset key={group.key} className="m-0 min-w-0 border-0 p-0">
          <legend className="mb-2 p-0 font-mono text-xs uppercase tracking-wide text-muted">
            {group.label}
          </legend>
          <div className="flex flex-wrap gap-1.5">
            {group.values(facets).map((value) => {
              const selected = searchParams.get(group.key) === value;
              return (
                <button
                  key={value}
                  type="button"
                  aria-pressed={selected}
                  onClick={() => toggle(group.key, value)}
                  className={`rounded-md border px-2.5 py-1 font-mono text-xs capitalize ${
                    selected
                      ? 'border-accent bg-accent/10 text-accent'
                      : 'border-edge-strong text-muted hover:text-content'
                  }`}
                >
                  {value}
                </button>
              );
            })}
          </div>
        </fieldset>
      ))}
    </form>
  );
}
