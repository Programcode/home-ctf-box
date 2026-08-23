import type { NextRequest } from 'next/server';

const API_BASE_URL = process.env.ORIGIN_API_URL ?? 'http://localhost:8700';

/**
 * Same-origin proxy to the FastAPI server.
 *
 * Browser code calls `/api/or/<rest>` (for example `/api/or/labs`); this
 * handler forwards method, query string, JSON body, cookies and the
 * `x-csrf-token` header to `${ORIGIN_API_URL}/api/<rest>` and relays the
 * upstream response, including every Set-Cookie header. The httpOnly
 * session cookie and the readable CSRF cookie therefore live on the web
 * origin, so no CORS and no cross-site cookie rules are involved.
 */

const SKIPPED_RESPONSE_HEADERS = new Set(['content-length', 'transfer-encoding', 'connection']);

async function handle(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const incomingUrl = new URL(request.url);
  const target = `${API_BASE_URL}/api/${path.join('/')}${incomingUrl.search}`;

  const headers = new Headers();
  for (const name of ['cookie', 'content-type', 'x-csrf-token', 'accept']) {
    const value = request.headers.get(name);
    if (value !== null) {
      headers.set(name, value);
    }
  }
  headers.set('user-agent', request.headers.get('user-agent') ?? 'openrange-web');

  const hasBody = request.method !== 'GET' && request.method !== 'HEAD';
  const body = hasBody ? await request.arrayBuffer() : undefined;

  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method: request.method,
      headers,
      body,
      redirect: 'manual',
      cache: 'no-store',
    });
  } catch {
    return Response.json(
      { type: 'about:blank', title: 'Bad Gateway', status: 502 },
      { status: 502 },
    );
  }

  const responseHeaders = new Headers();
  for (const [name, value] of upstream.headers) {
    if (!SKIPPED_RESPONSE_HEADERS.has(name)) {
      responseHeaders.append(name, value);
    }
  }
  for (const cookie of upstream.headers.getSetCookie()) {
    responseHeaders.append('set-cookie', cookie);
  }

  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: responseHeaders,
  });
}

export { handle as GET, handle as POST, handle as PATCH, handle as PUT, handle as DELETE };

export const dynamic = 'force-dynamic';
