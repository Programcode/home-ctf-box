import type { Metadata } from 'next';
import { NotificationsView } from '@/components/NotificationsView';

export const metadata: Metadata = { title: 'Notifications' };

export default function NotificationsPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-10 sm:px-6 sm:py-14">
      <header>
        <h1 className="m-0 text-2xl font-semibold tracking-tight sm:text-3xl">Notifications</h1>
        <p className="mt-2 mb-0 max-w-[60ch] text-sm leading-relaxed text-muted">
          Unread items first. Control channels and muted categories below the feed.
        </p>
      </header>
      <div className="mt-8">
        <NotificationsView />
      </div>
    </div>
  );
}
