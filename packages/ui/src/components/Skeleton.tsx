import type { CSSProperties } from 'react';

export interface SkeletonProps {
  width?: string;
  height?: string;
  /** Accessible name for the loading region; content stays aria-hidden. */
  label: string;
  className?: string;
}

/**
 * Loading placeholder with shimmer animation (disabled under reduced motion).
 * The decorative block is hidden from assistive tech; the label is exposed on
 * the wrapper so screen readers announce the loading state.
 */
export function Skeleton({ width, height, label, className }: SkeletonProps) {
  const style: CSSProperties = {};
  if (width !== undefined) {
    style.width = width;
  }
  if (height !== undefined) {
    style.height = height;
  }
  return (
    <div role="status" aria-label={label}>
      <div
        aria-hidden="true"
        className={['or-skeleton', className].filter(Boolean).join(' ')}
        style={style}
      />
    </div>
  );
}
