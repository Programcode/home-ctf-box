import { readFileSync, readdirSync } from 'node:fs';
import path from 'node:path';
import { cache } from 'react';
import { parse } from 'yaml';

/**
 * Build-time/dev-time loader for the room catalog.
 *
 * The catalog API phase lands later; until then the source of truth is the
 * declarative content bundles under content/rooms (one room.yaml per room),
 * validated with the same field enums as packages/content-sdk.
 */

const DIFFICULTIES = ['beginner', 'easy', 'medium', 'hard', 'insane'] as const;
const ROOM_TYPES = ['guided', 'challenge', 'box', 'investigation', 'range'] as const;
const TRACKS = [
  'web-foundations',
  'linux-networking',
  'windows-ad',
  'crypto-binary',
  'defense-cloud',
] as const;

export type Difficulty = (typeof DIFFICULTIES)[number];
export type RoomType = (typeof ROOM_TYPES)[number];
export type Track = (typeof TRACKS)[number];

export interface RoomSummary {
  slug: string;
  title: string;
  difficulty: Difficulty;
  type: RoomType;
  track: Track;
  points: number;
  estimatedMinutes: number;
  tasksCount: number;
}

export interface RoomDetail extends RoomSummary {
  summary: string;
  objectives: string[];
  tags: string[];
  version: string;
  workstation: string | null;
}

export function contentRoomsDir(): string {
  return (
    process.env.OPENRANGE_CONTENT_DIR ?? path.resolve(process.cwd(), '..', '..', 'content', 'rooms')
  );
}

function isString(value: unknown): value is string {
  return typeof value === 'string';
}

function fail(roomDir: string, message: string): never {
  throw new Error(`Invalid room bundle at ${roomDir}: ${message}`);
}

function parseRoomFile(roomDir: string, fileName: string): RoomDetail {
  const raw = readFileSync(path.join(roomDir, fileName), 'utf8');
  const doc: unknown = parse(raw);
  if (typeof doc !== 'object' || doc === null || !('metadata' in doc) || !('spec' in doc)) {
    fail(roomDir, 'document must contain metadata and spec');
  }
  const docRecord = doc as Record<string, unknown>;
  const metadata = docRecord['metadata'];
  const spec = docRecord['spec'];
  if (
    typeof metadata !== 'object' ||
    metadata === null ||
    typeof spec !== 'object' ||
    spec === null
  ) {
    fail(roomDir, 'metadata and spec must be mappings');
  }

  const meta = metadata as Record<string, unknown>;
  const specRecord = spec as Record<string, unknown>;

  const slug = meta['slug'];
  if (!isString(slug) || slug.length === 0) {
    fail(roomDir, 'metadata.slug must be a non-empty string');
  }
  const dirName = path.basename(roomDir);
  if (slug !== dirName) {
    fail(roomDir, `metadata.slug "${slug}" does not match directory name "${dirName}"`);
  }
  const title = meta['title'];
  if (!isString(title) || title.length === 0) {
    fail(roomDir, 'metadata.title must be a non-empty string');
  }

  const difficulty = meta['difficulty'];
  if (!isDifficulty(difficulty)) {
    fail(roomDir, `metadata.difficulty must be one of ${DIFFICULTIES.join(', ')}`);
  }
  const track = specRecord['track'];
  if (!isTrack(track)) {
    fail(roomDir, `spec.track must be one of ${TRACKS.join(', ')}`);
  }
  const type = specRecord['type'];
  if (!isRoomType(type)) {
    fail(roomDir, `spec.type must be one of ${ROOM_TYPES.join(', ')}`);
  }

  const points = meta['points'];
  if (typeof points !== 'number' || !Number.isFinite(points) || points < 0) {
    fail(roomDir, 'metadata.points must be a non-negative number');
  }
  const estimatedMinutes = meta['estimated_minutes'];
  if (
    typeof estimatedMinutes !== 'number' ||
    !Number.isFinite(estimatedMinutes) ||
    estimatedMinutes < 0
  ) {
    fail(roomDir, 'metadata.estimated_minutes must be a non-negative number');
  }

  const tasks = specRecord['tasks'];
  if (!Array.isArray(tasks) || tasks.length === 0) {
    fail(roomDir, 'spec.tasks must be a non-empty list');
  }
  for (const task of tasks) {
    if (typeof task !== 'object' || task === null) {
      fail(roomDir, 'every task must be a mapping');
    }
  }

  const version = meta['version'];
  const objectives = specRecord['objectives'];
  const tags = meta['tags'];
  const workstation = specRecord['workstation'];

  return {
    slug,
    title,
    difficulty,
    type,
    track,
    points,
    estimatedMinutes,
    tasksCount: tasks.length,
    version: isString(version) ? version : '0.0.0',
    summary: isString(specRecord['summary']) ? (specRecord['summary'] as string).trim() : '',
    objectives: Array.isArray(objectives) ? objectives.filter(isString) : [],
    tags: Array.isArray(tags) ? tags.filter(isString) : [],
    workstation: isString(workstation) ? workstation : null,
  };
}

function isDifficulty(value: unknown): value is Difficulty {
  return isString(value) && DIFFICULTIES.includes(value as Difficulty);
}

function isRoomType(value: unknown): value is RoomType {
  return isString(value) && ROOM_TYPES.includes(value as RoomType);
}

function isTrack(value: unknown): value is Track {
  return isString(value) && TRACKS.includes(value as Track);
}

/** All rooms sorted by difficulty then points. Cached per server render pass. */
export const listRooms = cache((): RoomSummary[] => {
  const roomsDir = contentRoomsDir();
  if (!readdirSafe(roomsDir)) {
    return [];
  }
  const rooms: RoomSummary[] = [];
  for (const entry of readdirSync(roomsDir, { withFileTypes: true })) {
    if (!entry.isDirectory()) {
      continue;
    }
    const roomDir = path.join(roomsDir, entry.name);
    if (!readdirSync(roomDir).includes('room.yaml')) {
      continue;
    }
    rooms.push(toSummary(parseRoomFile(roomDir, 'room.yaml')));
  }
  const order = new Map<Difficulty, number>(DIFFICULTIES.map((d, i) => [d, i]));
  return rooms.sort((a, b) => {
    const diffDelta = (order.get(a.difficulty) ?? 0) - (order.get(b.difficulty) ?? 0);
    return diffDelta !== 0 ? diffDelta : a.points - b.points;
  });
});

function readdirSafe(dir: string): boolean {
  try {
    readdirSync(dir);
    return true;
  } catch {
    return false;
  }
}

function toSummary(detail: RoomDetail): RoomSummary {
  return {
    slug: detail.slug,
    title: detail.title,
    difficulty: detail.difficulty,
    type: detail.type,
    track: detail.track,
    points: detail.points,
    estimatedMinutes: detail.estimatedMinutes,
    tasksCount: detail.tasksCount,
  };
}

export const getRoom = cache((slug: string): RoomDetail | undefined => {
  const roomsDir = contentRoomsDir();
  const roomDir = path.join(roomsDir, slug);
  // slug is constrained to a plain directory name; no traversal possible.
  if (slug.includes('/') || slug.includes('\\') || !readdirSafe(roomDir)) {
    return undefined;
  }
  if (!readdirSync(roomDir).includes('room.yaml')) {
    return undefined;
  }
  return parseRoomFile(roomDir, 'room.yaml');
});

/** Distinct filter values that actually occur in the catalog. */
export const catalogFacets = cache(() => {
  const rooms = listRooms();
  return {
    difficulties: [...new Set(rooms.map((room) => room.difficulty))],
    types: [...new Set(rooms.map((room) => room.type))],
    tracks: [...new Set(rooms.map((room) => room.track))],
  };
});
