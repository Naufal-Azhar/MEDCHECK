import * as env from '$app/env/private';
import { Pool, type PoolConfig } from 'pg';
import { ConfigurationError } from './config';

export interface Database {
  query(text: string, values?: unknown[]): Promise<{ rows: Record<string, unknown>[] }>;
}

export function databaseOptions(): PoolConfig {
  const common = { max: 10, connectionTimeoutMillis: 10_000, idleTimeoutMillis: 30_000,
    query_timeout: 15_000, statement_timeout: 15_000, application_name: 'forge-sveltekit' };
  if (env.DATABASE_URL) {
    return { ...common, connectionString: env.DATABASE_URL.replace(/^postgresql\+psycopg:\/\//u, 'postgresql://') };
  }
  const port = Number(env.POSTGRES_PORT || env.PGPORT || '5433');
  if (!Number.isInteger(port) || port < 1 || port > 65535) throw new ConfigurationError('Invalid database port.');
  return { ...common, host: env.PGHOST || 'localhost', port,
    database: env.POSTGRES_DB || env.PGDATABASE || 'forgehacks',
    user: env.POSTGRES_USER || env.PGUSER || 'forgehacks',
    password: env.POSTGRES_PASSWORD || env.PGPASSWORD || 'forgehacks_dev' };
}

let pool: Pool | undefined;
export function getDatabase(): Database {
  if (!pool) {
    pool = new Pool(databaseOptions());
    // Idle-client errors must not crash the process or disclose connection details.
    pool.on('error', () => {});
  }
  return pool;
}

export async function closeDatabase(): Promise<void> {
  const current = pool;
  pool = undefined;
  await current?.end();
}

export function databaseId(value: unknown): number {
  if ((typeof value !== 'number' && typeof value !== 'string') ||
      (typeof value === 'string' && !/^\d+$/u.test(value))) throw new Error('Invalid database identifier.');
  const id = Number(value);
  if (!Number.isSafeInteger(id) || id < 1) throw new Error('Invalid database identifier.');
  return id;
}
