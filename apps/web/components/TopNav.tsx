import Link from 'next/link';
import { getCurrentUser } from '@/lib/api-server';
import { CommandPalette } from './CommandPalette';
import { LogoutButton } from './LogoutButton';
import { MobileNav } from './MobileNav';
import { NavLink } from './NavLink';

export async function TopNav() {
  const user = await getCurrentUser();

  const links = [
    { href: '/catalog', label: 'Catalog' },
    { href: '/dashboard', label: 'Dashboard' },
    { href: '/learn', label: 'Learn' },
    { href: '/challenges', label: 'Challenges' },
    { href: '/terminal', label: 'Terminal' },
    { href: '/notifications', label: 'Notifications' },
    ...(user === null ? [] : [{ href: '/profile', label: 'Profile' }]),
  ];

  return (
    <header className="relative border-b border-edge bg-panel">
      <nav
        aria-label="Main navigation"
        className="mx-auto flex h-14 max-w-6xl items-center gap-2 px-4 sm:gap-4 sm:px-6"
      >
        <Link
          href="/"
          className="font-mono text-sm font-bold tracking-tight text-content no-underline"
        >
          Open<span className="text-accent">Range</span>
        </Link>
        <ul className="ml-1 hidden list-none items-center gap-1 p-0 text-sm md:flex">
          {links.map((link) => (
            <li key={link.href}>
              <NavLink href={link.href}>
                <span className="inline-block px-2 py-2 sm:px-2.5">{link.label}</span>
              </NavLink>
            </li>
          ))}
        </ul>
        <div className="ml-auto flex items-center gap-3">
          <CommandPalette authenticated={user !== null} />
          <MobileNav links={links} />
          {user === null ? (
            <Link
              href="/login"
              className="rounded-md border border-edge-strong px-3 py-1.5 text-sm text-content no-underline hover:border-muted"
            >
              Sign in
            </Link>
          ) : (
            <span className="flex items-center gap-2 text-sm">
              <span className="hidden font-mono text-xs text-muted sm:inline">{user.username}</span>
              <LogoutButton />
            </span>
          )}
        </div>
      </nav>
    </header>
  );
}
