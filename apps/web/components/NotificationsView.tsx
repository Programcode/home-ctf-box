'use client';

import { useEffect, useState } from 'react';
import { Badge, Button, Skeleton, useToast } from '@openrange/ui';
import type { NotificationFeed, NotificationItem, NotificationPrefs } from '@openrange/contracts';
import { apiProxy, isAuthError, ProxyError } from '@/lib/api-browser';
import { SignInPrompt } from './SignInPrompt';

const CATEGORIES = ['lab_expiry', 'announcement', 'achievement', 'assignment', 'system'] as const;

const CATEGORY_LABEL: Record<string, string> = {
  lab_expiry: 'Lab expiry',
  announcement: 'Announcement',
  achievement: 'Achievement',
  assignment: 'Assignment',
  system: 'System',
};

type Load =
  | { kind: 'loading' }
  | { kind: 'signedOut' }
  | { kind: 'error'; message: string }
  | { kind: 'ready'; feed: NotificationFeed; prefs: NotificationPrefs | null };

function payloadText(item: NotificationItem): { title: string; body: string | null } {
  const payload = item.payload;
  const title = typeof payload['title'] === 'string' ? payload['title'] : null;
  const body = typeof payload['body'] === 'string' ? payload['body'] : null;
  return {
    title: title ?? CATEGORY_LABEL[item.category] ?? item.category,
    body,
  };
}

export function NotificationsView() {
  const [load, setLoad] = useState<Load>({ kind: 'loading' });
  const [savingPrefs, setSavingPrefs] = useState(false);
  const toast = useToast();

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      apiProxy<NotificationFeed>('notifications/me'),
      apiProxy<NotificationPrefs>('notifications/me/prefs').catch(() => null),
    ]).then(
      ([feed, prefs]) => {
        if (!cancelled) {
          setLoad({ kind: 'ready', feed, prefs });
        }
      },
      (error: unknown) => {
        if (cancelled) {
          return;
        }
        if (isAuthError(error)) {
          setLoad({ kind: 'signedOut' });
        } else {
          setLoad({
            kind: 'error',
            message: error instanceof ProxyError ? error.message : 'Could not reach the server.',
          });
        }
      },
    );
    return () => {
      cancelled = true;
    };
  }, []);

  async function markRead(id: string) {
    try {
      await apiProxy(`notifications/${encodeURIComponent(id)}/read`, { method: 'POST', json: {} });
      setLoad((current) =>
        current.kind === 'ready'
          ? {
              ...current,
              feed: {
                ...current.feed,
                items: current.feed.items.map((item) =>
                  item.id === id && item.read_at === null
                    ? { ...item, read_at: new Date().toISOString() }
                    : item,
                ),
              },
            }
          : current,
      );
    } catch (error) {
      toast.push({
        title: 'Could not mark as read',
        description: error instanceof ProxyError ? error.message : undefined,
        variant: 'error',
      });
    }
  }

  async function readAll() {
    try {
      await apiProxy('notifications/read-all', { method: 'POST', json: {} });
      setLoad((current) =>
        current.kind === 'ready'
          ? {
              ...current,
              feed: {
                ...current.feed,
                items: current.feed.items.map((item) => ({
                  ...item,
                  read_at: item.read_at ?? new Date().toISOString(),
                })),
              },
            }
          : current,
      );
      toast.push({ title: 'All notifications marked read', variant: 'success' });
    } catch (error) {
      toast.push({
        title: 'Could not mark all as read',
        description: error instanceof ProxyError ? error.message : undefined,
        variant: 'error',
      });
    }
  }

  async function savePrefs(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (load.kind !== 'ready' || load.prefs === null) {
      return;
    }
    const form = new FormData(event.currentTarget);
    setSavingPrefs(true);
    try {
      const updated = await apiProxy<NotificationPrefs>('notifications/me/prefs', {
        method: 'PUT',
        json: {
          channel_in_app: form.get('channel_in_app') === 'on',
          channel_email: form.get('channel_email') === 'on',
          digest_weekly: form.get('digest_weekly') === 'on',
          muted_categories: CATEGORIES.filter((category) => form.get(`mute-${category}`) === 'on'),
        },
      });
      setLoad((current) => (current.kind === 'ready' ? { ...current, prefs: updated } : current));
      toast.push({ title: 'Preferences saved', variant: 'success' });
    } catch (error) {
      toast.push({
        title: 'Could not save preferences',
        description: error instanceof ProxyError ? error.message : undefined,
        variant: 'error',
      });
    } finally {
      setSavingPrefs(false);
    }
  }

  if (load.kind === 'loading') {
    return (
      <div className="mt-8 grid gap-3" aria-busy="true">
        {[0, 1, 2, 3].map((slot) => (
          <Skeleton key={slot} label="Loading notifications" width="100%" height="4rem" />
        ))}
      </div>
    );
  }

  if (load.kind === 'signedOut') {
    return <SignInPrompt what="see your notifications" />;
  }

  if (load.kind === 'error') {
    return (
      <p
        role="alert"
        className="mt-8 rounded-md border border-warning bg-panel px-4 py-3 text-sm text-warning"
      >
        {load.message}
      </p>
    );
  }

  const unread = load.feed.items.filter((item) => item.read_at === null).length;
  const prefs = load.prefs;

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p aria-live="polite" className="mb-0 font-mono text-xs uppercase tracking-wide text-muted">
          {unread} unread of {load.feed.total}
        </p>
        <Button
          size="sm"
          variant="secondary"
          disabled={unread === 0}
          onClick={() => void readAll()}
        >
          Mark all read
        </Button>
      </div>

      <ul className="mt-4 mb-0 grid list-none gap-2 p-0">
        {load.feed.items.length === 0 ? (
          <li className="rounded-lg border border-dashed border-edge-strong bg-panel px-5 py-10 text-center text-sm text-muted">
            Nothing here yet. Lab expiries, announcements and achievements land in this feed.
          </li>
        ) : (
          load.feed.items.map((item) => {
            const text = payloadText(item);
            const isUnread = item.read_at === null;
            return (
              <li
                key={item.id}
                className={[
                  'flex flex-wrap items-center justify-between gap-3 rounded-lg border px-4 py-3',
                  isUnread ? 'border-edge-strong bg-panel' : 'border-edge bg-transparent',
                ].join(' ')}
              >
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    {isUnread ? (
                      <span aria-hidden="true" className="h-2 w-2 rounded-full bg-accent" />
                    ) : null}
                    <Badge variant={isUnread ? 'default' : 'default'}>
                      {CATEGORY_LABEL[item.category] ?? item.category}
                    </Badge>
                    <span className={isUnread ? 'font-semibold text-content' : 'text-muted'}>
                      {text.title}
                    </span>
                  </div>
                  {text.body !== null ? (
                    <p className="mb-0 mt-1 text-sm leading-relaxed text-muted">{text.body}</p>
                  ) : null}
                  <p className="mb-0 mt-1 font-mono text-[0.7rem] uppercase tracking-wide text-muted">
                    {new Date(item.created_at).toLocaleString()}
                  </p>
                </div>
                {isUnread ? (
                  <Button size="sm" variant="ghost" onClick={() => void markRead(item.id)}>
                    Mark read
                  </Button>
                ) : (
                  <span className="font-mono text-xs uppercase tracking-wide text-muted">read</span>
                )}
              </li>
            );
          })
        )}
      </ul>

      {prefs !== null ? (
        <section
          aria-labelledby="prefs-heading"
          className="mt-10 rounded-lg border border-edge bg-panel px-5 py-5"
        >
          <h2 id="prefs-heading" className="m-0 text-base font-semibold">
            Notification preferences
          </h2>
          <form onSubmit={savePrefs} className="mt-4">
            <fieldset className="m-0 border-0 p-0">
              <legend className="mb-2 p-0 font-mono text-xs uppercase tracking-wide text-muted">
                Channels
              </legend>
              <label className="flex items-center gap-2 py-1 text-sm">
                <input
                  type="checkbox"
                  name="channel_in_app"
                  defaultChecked={prefs.channel_in_app}
                  className="accent-[var(--or-accent)]"
                />
                In-app notifications
              </label>
              <label className="flex items-center gap-2 py-1 text-sm">
                <input
                  type="checkbox"
                  name="channel_email"
                  defaultChecked={prefs.channel_email}
                  className="accent-[var(--or-accent)]"
                />
                Email
              </label>
              <label className="flex items-center gap-2 py-1 text-sm">
                <input
                  type="checkbox"
                  name="digest_weekly"
                  defaultChecked={prefs.digest_weekly}
                  className="accent-[var(--or-accent)]"
                />
                Weekly digest
              </label>
            </fieldset>

            <fieldset className="m-0 mt-4 border-0 p-0">
              <legend className="mb-2 p-0 font-mono text-xs uppercase tracking-wide text-muted">
                Muted categories
              </legend>
              <div className="grid sm:grid-cols-2">
                {CATEGORIES.map((category) => (
                  <label key={category} className="flex items-center gap-2 py-1 text-sm">
                    <input
                      type="checkbox"
                      name={`mute-${category}`}
                      defaultChecked={prefs.muted_categories.includes(category)}
                      className="accent-[var(--or-accent)]"
                    />
                    {CATEGORY_LABEL[category]}
                  </label>
                ))}
              </div>
            </fieldset>

            <div className="mt-4">
              <Button type="submit" disabled={savingPrefs}>
                {savingPrefs ? 'Saving...' : 'Save preferences'}
              </Button>
            </div>
          </form>
        </section>
      ) : null}
    </>
  );
}
