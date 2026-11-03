import type { Handle, HandleServerError } from '@sveltejs/kit/hooks';
import { apiError, requestId } from '#lib/server/http.ts';

export const handle: Handle = async ({ event, resolve }) => {
  const id = requestId(event.request.headers.get('X-Request-ID'));
  event.locals.requestId = id;
  let response: Response;
  try { response = await resolve(event); }
  catch { response = apiError('Service unavailable', id, 503); }
  // Clone headers: redirects and some platform responses have immutable headers.
  const headers = new Headers(response.headers);
  headers.set('X-Request-ID', id);
  headers.set('Cache-Control', 'no-store');
  headers.set('X-Content-Type-Options', 'nosniff');
  return new Response(response.body, { status: response.status, statusText: response.statusText, headers });
};

export const handleError: HandleServerError = ({ event }) => ({
  message: 'Service unavailable', request_id: event.locals.requestId,
});
