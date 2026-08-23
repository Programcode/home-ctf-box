import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Badge } from '../src/components/Badge';

describe('Badge', () => {
  it('renders its text content for assistive technology', () => {
    render(<Badge>medium</Badge>);
    const badge = screen.getByText('medium');
    expect(badge).toBeInTheDocument();
    expect(badge).not.toHaveAttribute('aria-hidden', 'true');
  });

  it('renders as a non-interactive element without a widget role', () => {
    render(<Badge>beginner</Badge>);
    expect(screen.getByText('beginner').tagName).toBe('SPAN');
    expect(screen.queryByRole('button')).toBeNull();
  });

  it('applies the variant class and data attribute for each variant', () => {
    for (const variant of ['default', 'success', 'warning', 'danger'] as const) {
      const { container, unmount } = render(<Badge variant={variant}>state</Badge>);
      const badge = container.querySelector('span.or-badge');
      expect(badge?.className).toContain(`or-badge--${variant}`);
      expect(badge?.getAttribute('data-variant')).toBe(variant);
      unmount();
    }
  });

  it('keeps the default variant class when no variant is given', () => {
    render(<Badge>275 pts</Badge>);
    expect(screen.getByText('275 pts').className).toContain('or-badge--default');
  });
});
