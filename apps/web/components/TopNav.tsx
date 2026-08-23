import Link from 'next/link';
import { getCurrentUser } from '@/lib/api-server';
import { CommandPalette } from './CommandPalette';
import { LogoutButton } from './LogoutButton';

export async function TopNav() {
  const user = await getCurrentUser();

  return (
    <header className="border-b border-edge bg-panel">
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
        <ul className="ml-1 flex list-none items-center gap-0.5 p-0 text-sm sm:ml-2 sm:gap-1">
          <li>
            <Link
              href="/catalog"
              className="inline-block rounded-md px-2 py-2 text-muted hover:text-content sm:px-3"
            >
              Catalog
            </Link>
          </li>
          <li>
            <Link
              href="/dashboard"
              className="inline-block rounded-md px-2 py-2 text-muted hover:text-content sm:px-3"
            >
              Dashboard
            </Link>
          </li>
          {user !== null ? (
            <li>
              <Link
                href="/profile"
                className="inline-block rounded-md px-2 py-2 text-muted hover:text-content sm:px-3"
              >
                Profile
              </Link>
            </li>
          ) : null}
        </ul>
        <div className="ml-auto flex items-center gap-3">
          <CommandPalette authenticated={user !== null} />
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
