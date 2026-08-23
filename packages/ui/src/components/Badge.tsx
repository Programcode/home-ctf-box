import type { HTMLAttributes } from 'react';

export type BadgeVariant = 'default' | 'success' | 'warning' | 'danger';

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

/**
 * Compact mono label for statuses, difficulties and counts.
 * Decorative by itself; pair with visually hidden text when the color alone
 * carries meaning. Server-component safe.
 */
export function Badge({ variant = 'default', className, ...rest }: BadgeProps) {
  return (
    <span
      className={['or-badge', `or-badge--${variant}`, className].filter(Boolean).join(' ')}
      data-variant={variant}
      {...rest}
    />
  );
}
