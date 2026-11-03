import { randomUUID } from 'node:crypto';
import { ConfigurationError, loadSettings } from './config';
import { generateAnswer, preflightAnswer } from './answer';
import { databaseId, getDatabase } from './db';
import { retrieveContext, validateRequest } from './retrieval';
import { isRecord, parseUniqueJson } from './json';

export const INVALID_REQUEST = 'Invalid request. Supply a question of 1–2000 characters and top_k of 1–20.';
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/iu;
export function requestId(value?: string | null): string {
  return value && UUID.test(value) ? value.toLowerCase() : randomUUID();
}

export function apiJson(data: unknown, id: string, status = 200): Response {
  return Response.json(data, { status, headers: { 'X-Request-ID': id, 'Cache-Control': 'no-store',
    'X-Content-Type-Options': 'nosniff' } });
}
export function apiError(detail: string, id: string, status: number): Response {
  return apiJson({ detail, request_id: id }, id, status);
}

const MAX_BODY_BYTES = 32_768;
async function questionPayload(request: Request): Promise<{ question: string; topK: number }> {
  const declared = request.headers.get('content-length');
  if (declared && (!/^\d+$/u.test(declared) || Number(declared) > MAX_BODY_BYTES)) throw new TypeError(INVALID_REQUEST);
  const contentType = request.headers.get('content-type')?.split(';')[0].trim().toLowerCase();
  if (contentType && contentType !== 'application/json') throw new TypeError(INVALID_REQUEST);
  if (!request.body) throw new TypeError(INVALID_REQUEST);
  const reader = request.body.getReader();
  const decoder = new TextDecoder('utf-8', { fatal: true });
  let text = '';
  let bytes = 0;
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      bytes += value.byteLength;
      if (bytes > MAX_BODY_BYTES) {
        void reader.cancel().catch(() => {});
        throw new TypeError(INVALID_REQUEST);
      }
      text += decoder.decode(value, { stream: true });
    }
    text += decoder.decode();
  } finally { reader.releaseLock(); }
  const data = parseUniqueJson(text);
  if (!isRecord(data)) throw new TypeError(INVALID_REQUEST);
  const topK = data.top_k === undefined ? 5 : data.top_k;
  const question = validateRequest(data.question, topK);
  return { question, topK: topK as number };
}

export interface ApiEvent {
  request: Request;
  locals: { requestId?: string };
}
function eventId(event: ApiEvent): string {
  return requestId(event.locals.requestId ?? event.request.headers.get('X-Request-ID'));
}

export async function questionResponse(event: ApiEvent, kind: 'chat' | 'search'): Promise<Response> {
  const id = eventId(event);
  let payload;
  try { payload = await questionPayload(event.request); }
  catch { return apiError(INVALID_REQUEST, id, 422); }
  const { question, topK } = payload;
  try {
    const preflight = preflightAnswer(question);
    if (preflight) {
      return apiJson(kind === 'chat' ? { request_id: id, ...preflight } : {
        request_id: id, question: '', hits: [], embedding_ms: 0, retrieval_ms: 0,
        notice: preflight.answer, status: preflight.status, safety_reason: preflight.safety_reason,
      }, id);
    }
    const settings = loadSettings();
    const { result, context } = await retrieveContext(question, topK, settings);
    if (kind === 'search') {
      return apiJson({ request_id: id, question,
        hits: result.hits.map(({ source_id: _sourceId, ...hit }, index) => ({ citation_id: `S${index + 1}`, ...hit })),
        embedding_ms: result.embedding_ms, retrieval_ms: result.retrieval_ms, notice: result.notice,
        status: 'retrieved', safety_reason: null }, id);
    }
    return apiJson({ request_id: id, ...await generateAnswer(context, settings) }, id);
  } catch (error) {
    if (kind === 'chat' && error instanceof ConfigurationError) return apiError('LLM service is not configured', id, 503);
    return apiError(kind === 'chat' ? 'Chat service unavailable' : 'Search service unavailable', id, 503);
  }
}

export async function healthResponse(event: ApiEvent): Promise<Response> {
  const id = eventId(event);
  try {
    await getDatabase().query('SELECT 1');
    return apiJson({ status: 'ok', service: 'forgehacks-healthcare-assistant', database: 'ok' }, id);
  } catch {
    return apiJson({ status: 'degraded', service: 'forgehacks-healthcare-assistant', database: 'unavailable' }, id);
  }
}

export async function sourceResponse(event: ApiEvent, sourceId: string | undefined): Promise<Response> {
  const id = eventId(event);
  if (!sourceId || !/^\d+$/u.test(sourceId) || !Number.isSafeInteger(Number(sourceId))) {
    return apiError('Invalid source identifier', id, 422);
  }
  try {
    const { rows } = await getDatabase().query(
      'SELECT id, name, base_url, authority_level, metadata FROM sources WHERE id = $1', [sourceId]);
    if (!rows.length) return apiError('Source not found', id, 404);
    const row = rows[0];
    return apiJson({ id: databaseId(row.id), name: row.name, base_url: row.base_url,
      authority_level: row.authority_level, metadata: row.metadata }, id);
  } catch { return apiError('Source service unavailable', id, 503); }
}
