import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { RequestEvent } from '@sveltejs/kit';

const { environment, query } = vi.hoisted(() => ({
  environment: {
      FEATHERLESS_API_KEY: undefined, FEATHERLESS_BASE_URL: undefined, FEATHERLESS_MODEL: undefined,
      FEATHERLESS_MAX_TOKENS: undefined, FEATHERLESS_TIMEOUT_SECONDS: undefined,
      DATABASE_URL: undefined, POSTGRES_PORT: undefined, POSTGRES_DB: undefined,
      POSTGRES_USER: undefined, POSTGRES_PASSWORD: undefined, PGHOST: undefined, PGPORT: undefined,
      PGDATABASE: undefined, PGUSER: undefined, PGPASSWORD: undefined,
    } as Record<string, string | undefined>, query: vi.fn(),
}));
vi.mock('$app/env/private', () => environment);
vi.mock('../src/lib/server/db', async (original) => ({
  ...await original<typeof import('../src/lib/server/db')>(), getDatabase: vi.fn(() => ({ query })),
}));
vi.mock('../src/lib/server/retrieval', async (original) => ({
  ...await original<typeof import('../src/lib/server/retrieval')>(), retrieveContext: vi.fn(),
}));
vi.mock('../src/lib/server/answer', async (original) => ({
  ...await original<typeof import('../src/lib/server/answer')>(), generateAnswer: vi.fn(),
}));
import { TEST_MODEL } from '../src/lib/server/config';
import { databaseOptions, getDatabase } from '../src/lib/server/db';
import { fallback, generateAnswer } from '../src/lib/server/answer';
import { retrieveContext, SEARCH_NOTICE } from '../src/lib/server/retrieval';
import { apiJson, INVALID_REQUEST, requestId } from '../src/lib/server/http';
import { POST as chat } from '../src/routes/chat/+server';
import { POST as search } from '../src/routes/search/+server';
import { GET as health } from '../src/routes/health/+server';
import { GET as source } from '../src/routes/sources/[id]/+server';
import { GET as docs } from '../src/routes/docs/+server';
import { handle, handleError } from '../src/hooks.server';

const ID = 'c82aac92-834b-4f7e-9abe-c387af32f949';
function event<T extends RequestEvent = RequestEvent>(path = '/chat', body: unknown = { question: 'What is hydration?' }, raw = false): T {
  return { request: new Request('http://localhost' + path, {
    method: body === undefined || ['/health', '/docs'].includes(path) || path.startsWith('/sources') ? 'GET' : 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Request-ID': ID },
    ...(!['/health', '/docs'].includes(path) && !path.startsWith('/sources') ? { body: raw ? String(body) : JSON.stringify(body) } : {}),
  }), locals: { requestId: ID }, params: { id: path.split('/').at(-1) }, url: new URL('http://localhost' + path) } as unknown as T;
}
const syntheticHit = { chunk_id: 1, document_id: 2, chunk_index: 0, source_id: 3, title: 'Synthetic topic',
  source: 'MedlinePlus', source_url: 'https://example.invalid/topic', content: 'Synthetic evidence.', similarity: 0.8 };
beforeEach(() => {
  vi.clearAllMocks();
  for (const key of Object.keys(environment)) environment[key] = undefined;
  environment.FEATHERLESS_API_KEY = 'synthetic-secret';
  environment.FEATHERLESS_MODEL = TEST_MODEL;
  query.mockResolvedValue({ rows: [] });
  vi.mocked(retrieveContext).mockResolvedValue({
    result: { request_id: 'internal-retrieval-id', hits: [syntheticHit], embedding_ms: 1, retrieval_ms: 2, notice: SEARCH_NOTICE },
    context: { question: 'What is hydration?', evidence: [], insufficient_evidence: true, prompt_context: '', insufficiency_reason: 'No evidence' },
  });
  vi.mocked(generateAnswer).mockResolvedValue(fallback('insufficient_evidence'));
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Tests must not access the network'); }));
});
afterEach(() => vi.unstubAllGlobals());

describe('API question contracts', () => {
  it.each([chat, search])('returns a private 422 for malformed input', async (handler) => {
    for (const body of [{ question: 'synthetic@example.invalid', top_k: true }, { question: '' },
      { question: 'x'.repeat(2001) }, { question: 'topic', top_k: 21 }, { question: 123 }, null]) {
      const response = await handler(event('/chat', body));
      expect(response.status).toBe(422);
      expect(await response.json()).toEqual({ detail: INVALID_REQUEST, request_id: ID });
      expect(response.headers.get('cache-control')).toBe('no-store');
    }
    expect(retrieveContext).not.toHaveBeenCalled();
  });
  it.each(['{"question":"secret",', '{"question":"first","question":"second"}', 'not json'])(
    'redacts malformed and duplicate-key JSON: %s', async (body) => {
      const response = await chat(event('/chat', body, true));
      expect(response.status).toBe(422);
      expect(await response.text()).not.toContain('secret');
    });
  it('bounds body bytes before parsing', async () => {
    const response = await chat(event('/chat', 'x'.repeat(33000), true));
    expect(response.status).toBe(422);
    expect(retrieveContext).not.toHaveBeenCalled();
  });
  it.each([chat, search])('screens sensitive questions without requiring settings, DB or inference', async (handler) => {
    environment.FEATHERLESS_API_KEY = undefined;
    const response = await handler(event('/chat', { question: 'synthetic@example.invalid' }));
    const data = await response.json();
    expect(response.status).toBe(200);
    expect(data).toMatchObject({ request_id: ID, status: 'privacy_refusal', safety_reason: 'personal_identifiers' });
    expect(JSON.stringify(data)).not.toContain('synthetic@example.invalid');
    expect(retrieveContext).not.toHaveBeenCalled();
    expect(generateAnswer).not.toHaveBeenCalled();
    expect(getDatabase).not.toHaveBeenCalled();
  });
  it('preserves search fields and keeps internal source/retrieval IDs private', async () => {
    const response = await search(event('/search', { question: '  What is hydration?  ' }));
    const data = await response.json();
    expect(data).toMatchObject({ request_id: ID, question: 'What is hydration?', embedding_ms: 1, retrieval_ms: 2,
      status: 'retrieved', safety_reason: null, hits: [{ citation_id: 'S1', chunk_id: 1, chunk_index: 0, document_id: 2 }] });
    expect(data.hits[0]).not.toHaveProperty('source_id');
    expect(retrieveContext).toHaveBeenCalledWith('What is hydration?', 5, expect.objectContaining({ model: TEST_MODEL }));
    expect(response.headers.get('x-request-id')).toBe(ID);
  });
  it('preserves the chat response contract', async () => {
    const response = await chat(event());
    expect(await response.json()).toEqual({ request_id: ID, ...fallback('insufficient_evidence') });
    expect(generateAnswer).toHaveBeenCalledTimes(1);
  });
  it('reports missing chat configuration without exposing settings', async () => {
    environment.FEATHERLESS_API_KEY = undefined;
    const response = await chat(event());
    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({ detail: 'LLM service is not configured', request_id: ID });
  });
  it.each([[chat, 'Chat'], [search, 'Search']] as const)('redacts upstream exceptions', async (handler, service) => {
    vi.mocked(retrieveContext).mockRejectedValueOnce(new Error('PRIVATE_QUESTION DSN synthetic-secret'));
    const response = await handler(event());
    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({ detail: `${service} service unavailable`, request_id: ID });
  });
});

describe('health, sources and discovery', () => {
  it('checks DB availability but never calls the provider', async () => {
    const response = await health(event('/health'));
    expect(await response.json()).toEqual({ status: 'ok', service: 'forgehacks-healthcare-assistant', database: 'ok' });
    query.mockRejectedValueOnce(new Error('private DSN'));
    const degraded = await health(event('/health'));
    expect(degraded.status).toBe(200);
    expect(await degraded.json()).toMatchObject({ status: 'degraded', database: 'unavailable' });
    expect(fetch).not.toHaveBeenCalled();
  });
  it('binds source IDs and normalizes bigint responses', async () => {
    query.mockResolvedValueOnce({ rows: [{ id: '3', name: 'MedlinePlus', base_url: 'https://medlineplus.gov',
      authority_level: 'authoritative', metadata: {} }] });
    const response = await source(event('/sources/3'));
    expect(await response.json()).toMatchObject({ id: 3, name: 'MedlinePlus', metadata: {} });
    expect(query).toHaveBeenCalledWith(expect.stringContaining('WHERE id = $1'), ['3']);
  });
  it('returns safe missing, invalid and unavailable source errors', async () => {
    expect((await source(event('/sources/3'))).status).toBe(404);
    expect((await source(event('/sources/1 OR 1=1'))).status).toBe(422);
    query.mockRejectedValueOnce(new Error('secret connection string'));
    const response = await source(event('/sources/3'));
    expect(response.status).toBe(503);
    expect(await response.text()).not.toContain('secret');
  });
  it('exposes JSON OpenAPI discovery without secrets', async () => {
    const response = await docs(event('/docs'));
    const document = await response.json();
    expect(document.openapi).toBe('3.1.0');
    expect(Object.keys(document.paths)).toEqual(expect.arrayContaining(['/chat', '/search', '/health', '/sources/{id}']));
    expect(JSON.stringify(document)).not.toContain('synthetic-secret');
  });
  it('uses Docker-compatible DB defaults and supports legacy psycopg URLs', () => {
    expect(databaseOptions()).toMatchObject({ host: 'localhost', port: 5433, database: 'forgehacks', user: 'forgehacks' });
    environment.DATABASE_URL = 'postgresql+psycopg://synthetic:secret@localhost:5433/synthetic';
    expect(databaseOptions().connectionString).toBe('postgresql://synthetic:secret@localhost:5433/synthetic');
  });
});

describe('request context hook', () => {
  it('accepts UUIDs only and rejects arbitrary header content', () => {
    expect(requestId(ID.toUpperCase())).toBe(ID);
    expect(requestId('private email or forged log line')).toMatch(/^[\da-f-]{36}$/u);
  });
  it('adds no-store and request IDs even for router errors', async () => {
    const current = event();
    const resolve = vi.fn(async () => new Response('Method not allowed', { status: 405 }));
    const response = await handle({ event: current, resolve } as Parameters<typeof handle>[0]);
    expect(response.headers.get('cache-control')).toBe('no-store');
    expect(response.headers.get('x-request-id')).toBe(ID);
    expect(current.locals.requestId).toBe(ID);
  });
  it('redacts unhandled failures', async () => {
    const current = event();
    const response = await handle({ event: current, resolve: async () => { throw new Error('SECRET'); } } as Parameters<typeof handle>[0]);
    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({ detail: 'Service unavailable', request_id: ID });
    const safe = await handleError({ kind: 'unknown', event: current, error: new Error('SECRET') });
    expect(safe).toEqual({ message: 'Service unavailable', request_id: ID });
  });
  it('keeps JSON errors private', () => {
    expect(apiJson({}, ID).headers.get('cache-control')).toBe('no-store');
  });
});
