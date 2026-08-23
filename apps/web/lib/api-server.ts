import 'server-only';

import { cookies } from 'next/headers';
import { ApiClient } from '@openrange/contracts';
import type { ApiError, CurrentUser } from '@openrange/contracts';

export const API_BASE_URL = process.env.ORIGIN_API_URL ?? 'http://localhost:8700';
export const SESSION_COOKIE = 'openrange_session';
export const CSRF_COOKIE = 'openrange_csrf';

/**
 * Server-side API client. The browser never talks to FastAPI directly:
 * every call either happens in a Server Component (this module, forwarding
 * the visitor's cookies) or goes through the same-origin route handler at
 * /api/or/* which proxies to FastAPI. See apps/web/README.md.
 */
export async function getServerApiClient(): Promise<ApiClient> {
  const store = await cookies();
  const session = store.get(SESSION_COOKIE)?.value;
  const csrf = store.get(CSRF_COOKIE)?.value;

  const fetchImpl: typeof fetch = (input, init = {}) => {
    const headers = new Headers(init.headers);
    if (session !== undefined) {
      headers.set('cookie', `${SESSION_COOKIE}=${session}`);
    }
    if (csrf !== undefined && init.method !== undefined && init.method !== 'GET') {
      headers.set('x-csrf-token', csrf);
    }
    return fetch(input, { ...init, headers });
  };

  return new ApiClient({ baseUrl: API_BASE_URL, fetchImpl, getCsrfToken: () => csrf });
}

export async function hasSessionCookie(): Promise<boolean> {
  const store = await cookies();
  return store.get(SESSION_COOKIE)?.value !== undefined;
}

/** Current user or null when signed out (401/403 from the API). */
export async function getCurrentUser(): Promise<CurrentUser | null> {
  if (!(await hasSessionCookie())) {
    return null;
  }
  try {
    return await (await getServerApiClient()).users.me();
  } catch (error) {
    if (isApiError(error) && (error.status === 401 || error.status === 403)) {
      return null;
    }
    throw error;
  }
}

function isApiError(error: unknown): error is ApiError {
  return error instanceof Error && error.name === 'ApiError';
}
