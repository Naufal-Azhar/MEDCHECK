import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { Settings } from '../src/lib/server/types';

const { environment } = vi.hoisted(() => ({ environment: {
  FEATHERLESS_API_KEY: undefined, FEATHERLESS_BASE_URL: undefined, FEATHERLESS_MODEL: undefined,
  FEATHERLESS_MAX_TOKENS: undefined, FEATHERLESS_TIMEOUT_SECONDS: undefined,
} as Record<string, string | undefined> }));
vi.mock('$app/env/private', () => environment);
import { ConfigurationError, loadSettings, PROVIDER_BASE_URL, TEST_MODEL } from '../src/lib/server/config';
import { complete, EmbeddingError, encodeQuery, encodeTexts, InferenceError, QUERY_INSTRUCTION } from '../src/lib/server/provider';

const settings: Settings = { apiKey: 'synthetic-secret', baseUrl: PROVIDER_BASE_URL, model: TEST_MODEL, maxTokens: 512, timeoutSeconds: 1 };
const messages = [{ role: 'user' as const, content: 'Synthetic educational question' }];
const valid = () => ({ choices: [{ finish_reason: 'stop', message: { content: 'synthetic content' } }],
  usage: { prompt_tokens: 12, completion_tokens: 3 } });
const fetchMock = vi.fn<typeof fetch>();
beforeEach(() => {
  for (const key of Object.keys(environment)) environment[key] = undefined;
  environment.FEATHERLESS_API_KEY = settings.apiKey;
  environment.FEATHERLESS_MODEL = settings.model;
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
});
afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); });

describe('private configuration and provider restrictions', () => {
  it('loads private settings without changing the environment', () => {
    expect(loadSettings()).toEqual({ ...settings, timeoutSeconds: 60 });
    expect(environment.FEATHERLESS_MAX_TOKENS).toBeUndefined();
  });
  it.each([
    ['FEATHERLESS_API_KEY', ''], ['FEATHERLESS_API_KEY', 'replace_me'], ['FEATHERLESS_API_KEY', 'key with spaces'],
    ['FEATHERLESS_BASE_URL', 'https://attacker.invalid/v1'], ['FEATHERLESS_BASE_URL', 'https://api.featherless.ai@attacker.invalid/v1'],
    ['FEATHERLESS_MODEL', 'other/expensive-model'], ['FEATHERLESS_MAX_TOKENS', '1.5'], ['FEATHERLESS_MAX_TOKENS', '1025'],
    ['FEATHERLESS_TIMEOUT_SECONDS', '0'], ['FEATHERLESS_TIMEOUT_SECONDS', '121'],
  ])('rejects invalid %s without network access', (name, value) => {
    environment[name] = value;
    expect(() => loadSettings()).toThrow(ConfigurationError);
    expect(fetchMock).not.toHaveBeenCalled();
  });
  it.each([
    { baseUrl: 'https://attacker.invalid/v1' }, { apiKey: '...' }, { model: 'other/expensive-model' },
    { maxTokens: 1025 }, { timeoutSeconds: 0 },
  ])('also validates directly constructed settings: %o', async (change) => {
    await expect(complete({ ...settings, ...change }, messages)).rejects.toThrow(ConfigurationError);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe('single-attempt completions', () => {
  it('uses locked model, bounded output, disabled redirects and local request IDs', async () => {
    fetchMock.mockResolvedValue(Response.json(valid()));
    const completion = await complete(settings, messages, 64);
    expect(completion).toMatchObject({ content: 'synthetic content', model: TEST_MODEL, prompt_tokens: 12, completion_tokens: 3 });
    expect(completion.request_id).toMatch(/^[\da-f-]{36}$/u);
    expect(completion.duration_ms).toBeGreaterThanOrEqual(0);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe(PROVIDER_BASE_URL + '/chat/completions');
    expect(options).toMatchObject({ redirect: 'error', cache: 'no-store', method: 'POST' });
    expect(JSON.parse(options!.body as string)).toEqual({ model: TEST_MODEL, messages, max_tokens: 64, temperature: 0, stream: false });
  });
  it.each([0, 513, 1.5, NaN])('rejects output override %s before fetch', async (limit) => {
    await expect(complete(settings, messages, limit)).rejects.toThrow();
    expect(fetchMock).not.toHaveBeenCalled();
  });
  it('rejects empty, extra-field and oversized messages', async () => {
    await expect(complete(settings, [])).rejects.toThrow();
    await expect(complete(settings, [{ role: 'user', content: ' ' }])).rejects.toThrow();
    await expect(complete(settings, [{ role: 'user', content: 'x'.repeat(12001) }])).rejects.toThrow();
    await expect(complete(settings, [{ ...messages[0], extra: true }] as unknown as typeof messages)).rejects.toThrow();
    expect(fetchMock).not.toHaveBeenCalled();
  });
  it.each([302, 401, 429, 500])('redacts HTTP %s and never retries', async (status) => {
    fetchMock.mockResolvedValue(new Response('PRIVATE_PROVIDER_BODY synthetic-secret', { status }));
    await expect(complete(settings, messages)).rejects.toThrow(InferenceError);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
  it('redacts network error details', async () => {
    fetchMock.mockRejectedValue(new Error('PRIVATE_PROMPT synthetic-secret'));
    await expect(complete(settings, messages)).rejects.toThrow('Featherless request failed; no automatic retry was made.');
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
  it('aborts on the configured timeout without retry', async () => {
    vi.useFakeTimers();
    fetchMock.mockImplementation((_url, options) => new Promise((_resolve, reject) => {
      options!.signal!.addEventListener('abort', () => reject(new Error('timeout secret')));
    }));
    const outcome = expect(complete(settings, messages)).rejects.toThrow(InferenceError);
    await vi.advanceTimersByTimeAsync(1000);
    await outcome;
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
  it.each([
    {}, { choices: [] }, { ...valid(), choices: [{ finish_reason: 'length', message: { content: 'partial' } }] },
    { ...valid(), choices: [{ finish_reason: 'stop', message: { content: '' } }] },
    { ...valid(), usage: { prompt_tokens: true, completion_tokens: 1 } },
    { ...valid(), usage: { prompt_tokens: 1, completion_tokens: -1 } },
  ])('rejects incomplete or malformed data: %o', async (data) => {
    fetchMock.mockResolvedValue(Response.json(data));
    await expect(complete(settings, messages)).rejects.toThrow(InferenceError);
  });
});

describe('remote embeddings', () => {
  const vector = () => [2, ...Array<number>(383).fill(0)];
  it('locks query instruction, model and dimensions, and normalizes vectors', async () => {
    fetchMock.mockResolvedValue(Response.json({ data: [{ index: 0, embedding: vector() }], usage: { prompt_tokens: 4 } }));
    const result = await encodeQuery('What is hydration?', settings);
    expect(result).toEqual([1, ...Array<number>(383).fill(0)]);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe(PROVIDER_BASE_URL + '/embeddings');
    expect(JSON.parse(options!.body as string)).toEqual({ model: 'Qwen/Qwen3-Embedding-4B',
      input: [QUERY_INSTRUCTION + 'What is hydration?'], dimensions: 384, encoding_format: 'float' });
  });
  it('orders batch results by verified index', async () => {
    fetchMock.mockResolvedValue(Response.json({ data: [{ index: 1, embedding: vector() }, { index: 0, embedding: vector() }],
      usage: { prompt_tokens: 8 } }));
    expect((await encodeTexts(['first', 'second'], settings)).vectors).toHaveLength(2);
  });
  it.each([
    { data: [{ index: 0, embedding: [1] }], usage: { prompt_tokens: 1 } },
    { data: [{ index: 0, embedding: Array(384).fill(0) }], usage: { prompt_tokens: 1 } },
    { data: [{ index: true, embedding: vector() }], usage: { prompt_tokens: 1 } },
    { data: [{ index: 0, embedding: [true, ...Array(383).fill(0)] }], usage: { prompt_tokens: 1 } },
    { data: [{ index: 0, embedding: vector() }], usage: { prompt_tokens: -1 } },
  ])('fails closed on invalid embeddings: %o', async (data) => {
    fetchMock.mockResolvedValue(Response.json(data));
    await expect(encodeTexts(['synthetic'], settings)).rejects.toThrow(EmbeddingError);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
  it('rejects duplicate batch indices', async () => {
    fetchMock.mockResolvedValue(Response.json({ data: [{ index: 0, embedding: vector() }, { index: 0, embedding: vector() }],
      usage: { prompt_tokens: 2 } }));
    await expect(encodeTexts(['first', 'second'], settings)).rejects.toThrow(EmbeddingError);
  });
  it('handles an empty batch locally and bounds inputs', async () => {
    expect(await encodeTexts([])).toEqual({ vectors: [], prompt_tokens: 0 });
    await expect(encodeQuery('x'.repeat(2001))).rejects.toThrow();
    await expect(encodeTexts(Array(33).fill('x'))).rejects.toThrow();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
