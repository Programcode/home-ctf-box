import Link from 'next/link';
import { Badge } from '@openrange/ui';
import type { BadgeVariant } from '@openrange/ui';

export interface RoomCardData {
  slug: string;
  title: string;
  difficulty: string;
  type: string;
  points: number;
  estimatedMinutes: number;
}

const DIFFICULTY_VARIANT = new Map<string, BadgeVariant>([
  ['beginner', 'default'],
  ['easy', 'success'],
  ['medium', 'warning'],
  ['hard', 'danger'],
  ['insane', 'danger'],
]);

export function RoomCard({ room }: { room: RoomCardData }) {
  return (
    <article className="relative flex h-full flex-col rounded-lg border border-edge bg-panel p-5 transition-colors hover:border-edge-strong">
      <div className="flex items-start justify-between gap-3">
        <h2 className="m-0 text-base font-semibold leading-snug">
          <Link
            href={`/catalog/${room.slug}`}
            className="text-content no-underline after:absolute after:inset-0 hover:text-accent"
          >
            {room.title}
          </Link>
        </h2>
        <span className="relative z-10">
          <Badge variant={DIFFICULTY_VARIANT.get(room.difficulty) ?? 'default'}>
            {room.difficulty}
          </Badge>
        </span>
      </div>
      <p className="mt-auto mb-0 pt-6 flex flex-wrap gap-x-4 gap-y-1 font-mono text-xs text-muted">
        <span>{room.type}</span>
        <span aria-hidden="true">·</span>
        <span>{room.points} pts</span>
        <span aria-hidden="true">·</span>
        <span>~{room.estimatedMinutes} min</span>
      </p>
    </article>
  );
}
