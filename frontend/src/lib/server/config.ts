import * as env from '$app/env/private';
import type { Settings } from './types';

export const PROVIDER_BASE_URL = 'https://api.featherless.ai/v1';
export const TEST_MODEL = 'Qwen/Qwen3-4B-Instruct-2507';

export class ConfigurationError extends Error {
  constructor(message = 'Service configuration is invalid.') {
    super(message);
    this.name = 'ConfigurationError';
  }
}

export function validateSettings(settings: Settings): void {
  if (settings.baseUrl !== PROVIDER_BASE_URL) throw new ConfigurationError('Unverified Featherless endpoint.');
  if (typeof settings.apiKey !== 'string' || !settings.apiKey ||
      ['...', 'your_api_key', 'replace_me'].includes(settings.apiKey.toLowerCase()) || /\s/u.test(settings.apiKey)) {
    throw new ConfigurationError('Invalid API key configuration.');
  }
  if (settings.model !== TEST_MODEL) throw new ConfigurationError('Only the approved testing model is enabled.');
  if (!Number.isInteger(settings.maxTokens) || settings.maxTokens < 1 || settings.maxTokens > 1024) {
    throw new ConfigurationError('Invalid configured output limit.');
  }
  if (!Number.isInteger(settings.timeoutSeconds) || settings.timeoutSeconds < 1 || settings.timeoutSeconds > 120) {
    throw new ConfigurationError('Invalid request timeout.');
  }
}

export function loadSettings(): Settings {
  const text = (name: keyof typeof env, fallback = '') => (env[name] || fallback).trim();
  const integer = (name: keyof typeof env, fallback: string) => {
    const value = text(name, fallback);
    if (!/^[+-]?\d+$/u.test(value)) throw new ConfigurationError('Token and timeout settings must be integers.');
    return Number(value);
  };
  const settings: Settings = {
    apiKey: text('FEATHERLESS_API_KEY'),
    baseUrl: text('FEATHERLESS_BASE_URL', PROVIDER_BASE_URL).replace(/\/+$/u, ''),
    model: text('FEATHERLESS_MODEL'),
    maxTokens: integer('FEATHERLESS_MAX_TOKENS', '512'),
    timeoutSeconds: integer('FEATHERLESS_TIMEOUT_SECONDS', '60'),
  };
  validateSettings(settings);
  return settings;
}
