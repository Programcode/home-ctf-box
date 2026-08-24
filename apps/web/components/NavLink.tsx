'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import type { ReactNode } from 'react';

export interface NavLinkProps {
  href: string;
  children: ReactNode;
  /** Called after activation; lets the mobile menu close itself. */
  onNavigate?: () => void;
}

/** Navigation link with `aria-current` and accent styling on the active route. */
export function NavLink({ href, children, onNavigate }: NavLinkProps) {
  const pathname = usePathname();
  const active = pathname === href || pathname.startsWith(`${href}/`);
  return (
    <Link
      href={href}
      aria-current={active ? 'page' : undefined}
      onClick={onNavigate}
      className={[
        'inline-block rounded-md no-underline',
        active
          ? 'text-content underline decoration-accent decoration-2 underline-offset-[6px]'
          : 'text-muted hover:text-content',
      ].join(' ')}
    >
      {children}
    </Link>
  );
}
