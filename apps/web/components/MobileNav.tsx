'use client';

import { useEffect, useRef, useState } from 'react';
import { NavLink } from './NavLink';

export interface MobileNavProps {
  links: readonly { href: string; label: string }[];
}

/** Disclosure navigation for narrow viewports; the desktop list stays inline. */
export function MobileNav({ links }: MobileNavProps) {
  const [open, setOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) {
      return;
    }
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false);
        buttonRef.current?.focus();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  const close = () => setOpen(false);

  return (
    <div className="md:hidden">
      <button
        ref={buttonRef}
        type="button"
        aria-expanded={open}
        aria-controls="mobile-nav-panel"
        onClick={() => setOpen((current) => !current)}
        className="rounded-md border border-edge px-2.5 py-1.5 text-sm text-content hover:border-muted"
      >
        {open ? 'Close menu' : 'Menu'}
      </button>
      {open ? (
        <nav
          id="mobile-nav-panel"
          aria-label="Mobile navigation"
          className="absolute inset-x-0 top-14 z-40 border-b border-edge bg-panel px-4 pb-4 pt-2 shadow-lg"
        >
          <ul className="flex list-none flex-col gap-1 p-0">
            {links.map((link) => (
              <li key={link.href}>
                <NavLink href={link.href} onNavigate={close}>
                  <span className="block px-1 py-2 text-sm">{link.label}</span>
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      ) : null}
    </div>
  );
}
