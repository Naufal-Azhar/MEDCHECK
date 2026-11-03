import { randomUUID } from 'node:crypto';
import { loadSettings, validateSettings } from './config';
import type { ChatMessage, Completion, Settings } from './types';
import { isRecord } from './json';

export const EMBEDDING_MODEL = 'Qwen/Qwen3-Embedding-4B';
export const EMBEDDING_DIMENSION = 384;
export const QUERY_INSTRUCTION = 'Instruct: Given a healthcare question, retrieve relevant passages that answer the question\nQuery: ';

export class InferenceError extends Error {
  constructor(message = 'Featherless request failed; no automatic retry was made.') {
    super(message);
    this.name = 'InferenceError';
  }
}
export class EmbeddingError extends Error {
  constructor() {
    super('Embedding request failed or returned invalid data; no retry made.');
    this.name = 'EmbeddingError';
  }
}

const length = (text: string) => Array.from(text).length;
const tokenCount = (value: unknown): value is number =>
  typeof value === 'number' && Number.isSafeInteger(value) && value >= 0;

async function post(settings: Settings, path: string, payload: unknown): Promise<unknown> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), settings.timeoutSeconds * 1000);
  try {
    const response = await fetch(settings.baseUrl + path, {
      method: 'POST', redirect: 'error', cache: 'no-store', signal: controller.signal,
      headers: { Authorization: `Bearer ${settings.apiKey}`, 'Content-Type': 'application/json',
        'X-Title': 'ForgeHacks Healthcare Information Assistant' },
      body: JSON.stringify(payload),
    });
    if (response.status !== 200) throw new InferenceError();
    return await response.json();
  } catch {
    // Never propagate provider bodies, prompts, URLs with credentials, or fetch error causes.
    throw new InferenceError();
  } finally {
    clearTimeout(timeout);
  }
}

export async function complete(settings: Settings, messages: ChatMessage[], maxTokens?: number): Promise<Completion> {
  validateSettings(settings);
  const limit = maxTokens ?? settings.maxTokens;
  if (!Number.isInteger(limit) || limit < 1 || limit > settings.maxTokens) {
    throw new RangeError('Output limit must not exceed the configured limit.');
  }
  if (!Array.isArray(messages) || messages.length < 1 || messages.length > 3 || messages.some((message) =>
    !isRecord(message) || Object.keys(message).sort().join(',') !== 'content,role' ||
    !['system', 'user', 'assistant'].includes(message.role) ||
    typeof message.content !== 'string' || !message.content.trim())) {
    throw new TypeError('Invalid chat messages.');
  }
  if (messages.reduce((total, message) => total + length(message.content), 0) > 12000) {
    throw new RangeError('Testing prompt exceeds the 12000-character limit.');
  }
  const request_id = randomUUID();
  const started = performance.now();
  const data = await post(settings, '/chat/completions', {
    model: settings.model, messages, max_tokens: limit, temperature: 0, stream: false,
  });
  if (!isRecord(data) || !Array.isArray(data.choices) || !isRecord(data.choices[0]) ||
      !isRecord(data.choices[0].message) || data.choices[0].finish_reason !== 'stop' ||
      typeof data.choices[0].message.content !== 'string' || !data.choices[0].message.content.trim() ||
      !isRecord(data.usage) || !tokenCount(data.usage.prompt_tokens) || !tokenCount(data.usage.completion_tokens)) {
    throw new InferenceError('Invalid or incomplete Featherless response; no automatic retry was made.');
  }
  return { content: data.choices[0].message.content, request_id, model: settings.model,
    prompt_tokens: data.usage.prompt_tokens, completion_tokens: data.usage.completion_tokens,
    duration_ms: performance.now() - started };
}

export async function encodeTexts(texts: string[], settings?: Settings): Promise<{ vectors: number[][]; prompt_tokens: number }> {
  if (!Array.isArray(texts) || texts.length > 32 || texts.some((text) =>
      typeof text !== 'string' || !text.trim() || length(text) > 10000)) {
    throw new TypeError('Invalid embedding input or batch size.');
  }
  if (!texts.length) return { vectors: [], prompt_tokens: 0 };
  const configured = settings ?? loadSettings();
  validateSettings(configured);
  try {
    const data = await post(configured, '/embeddings', {
      model: EMBEDDING_MODEL, input: texts, dimensions: EMBEDDING_DIMENSION, encoding_format: 'float',
    });
    if (!isRecord(data) || !Array.isArray(data.data) || data.data.length !== texts.length ||
        !isRecord(data.usage) || !tokenCount(data.usage.prompt_tokens)) throw new EmbeddingError();
    const vectors: number[][] = new Array(texts.length);
    const seen = new Set<number>();
    for (const row of data.data) {
      if (!isRecord(row) || typeof row.index !== 'number' || !Number.isInteger(row.index) ||
          row.index < 0 || row.index >= texts.length || seen.has(row.index) ||
          !Array.isArray(row.embedding) || row.embedding.length !== EMBEDDING_DIMENSION ||
          !row.embedding.every((value): value is number => typeof value === 'number' && Number.isFinite(value))) {
        throw new EmbeddingError();
      }
      const norm = Math.sqrt(row.embedding.reduce((sum, value) => sum + value * value, 0));
      if (!Number.isFinite(norm) || norm <= 0) throw new EmbeddingError();
      vectors[row.index] = row.embedding.map((value) => value / norm);
      seen.add(row.index);
    }
    return { vectors, prompt_tokens: data.usage.prompt_tokens };
  } catch {
    throw new EmbeddingError();
  }
}

export async function encodeQuery(question: string, settings?: Settings): Promise<number[]> {
  if (typeof question !== 'string' || !question.trim() || length(question) > 2000) {
    throw new TypeError('Query must contain 1–2000 characters.');
  }
  return (await encodeTexts([QUERY_INSTRUCTION + question], settings)).vectors[0];
}
