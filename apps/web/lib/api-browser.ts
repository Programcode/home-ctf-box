/** Browser-side helper for talking to the OpenRange API through the proxy. */

export const CSRF_COOKIE = 'openrange_csrf';

export function readCookie(name: string): string | undefined {
  const prefix = `${name}=`;
  for (const part of document.cookie.split(';')) {
    const value = part.trim();
    if (value.startsWith(prefix)) {
      return decodeURIComponent(value.slice(prefix.length));
    }
  }
  return undefined;
}

export interface ProblemResponse {
  title?: string;
  detail?: string;
  status?: number;
}

/** Same-origin fetch against the FastAPI proxy, attaching the CSRF header. */
export async function apiProxy<T>(
  path: string,
  init: RequestInit & { json?: unknown } = {},
): Promise<T> {
  const { json, ...rest } = init;
  const headers = new Headers(rest.headers);
  headers.set('accept', 'application/json');
  if (json !== undefined) {
    headers.set('content-type', 'application/json');
    rest.body = JSON.stringify(json);
  }
  const csrf = readCookie(CSRF_COOKIE);
  if (rest.method !== undefined && rest.method !== 'GET' && csrf !== undefined) {
    headers.set('x-csrf-token', csrf);
  }

  const response = await fetch(`/api/or/${path.replace(/^\//, '')}`, {
    ...rest,
    credentials: 'same-origin',
    headers,
  });
  const payload: unknown = await response.json().catch(() => undefined);

  if (!response.ok) {
    const problem = (payload ?? {}) as ProblemResponse;
    throw new ProxyError(
      problem.detail ?? problem.title ?? `Request failed (${response.status})`,
      response.status,
    );
  }
  return payload as T;
}

export class ProxyError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ProxyError';
    this.status = status;
  }
}
