import { defineEnvVars } from '@sveltejs/kit/env';

const optionalPrivate = {
  public: false,
  static: false,
  schema: (value: string | undefined) => value,
};

export const variables = defineEnvVars({
  FEATHERLESS_API_KEY: optionalPrivate,
  FEATHERLESS_BASE_URL: optionalPrivate,
  FEATHERLESS_MODEL: optionalPrivate,
  FEATHERLESS_MAX_TOKENS: optionalPrivate,
  FEATHERLESS_TIMEOUT_SECONDS: optionalPrivate,
  DATABASE_URL: optionalPrivate,
  POSTGRES_PORT: optionalPrivate,
  POSTGRES_DB: optionalPrivate,
  POSTGRES_USER: optionalPrivate,
  POSTGRES_PASSWORD: optionalPrivate,
  PGHOST: optionalPrivate,
  PGPORT: optionalPrivate,
  PGDATABASE: optionalPrivate,
  PGUSER: optionalPrivate,
  PGPASSWORD: optionalPrivate,
});
