// Exercise the actual Node build without external services or provider credits.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { createServer } from 'node:net';
import { setTimeout as delay } from 'node:timers/promises';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('..', import.meta.url));
const reservation = createServer();
reservation.listen(0, '127.0.0.1');
await once(reservation, 'listening');
const port = reservation.address().port;
await new Promise((resolve, reject) => reservation.close(error => error ? reject(error) : resolve()));
const origin = `http://127.0.0.1:${port}`;
const child = spawn(process.execPath, ['build/index.js'], {
  cwd: root,
  env: { ...process.env, HOST: '127.0.0.1', PORT: String(port), ORIGIN: origin,
    FEATHERLESS_API_KEY: '', FEATHERLESS_MODEL: '',
    DATABASE_URL: 'postgresql://synthetic:synthetic@127.0.0.1:1/synthetic' },
  stdio: ['ignore', 'ignore', 'ignore']
});
const stopped = once(child, 'exit');
let spawnError;
child.on('error', error => { spawnError = error; });
const id = 'c82aac92-834b-4f7e-9abe-c387af32f949';
async function request(path, question) {
  return fetch(new URL(path, origin + '/'), {
    ...(question === undefined ? {} : { method: 'POST', body: JSON.stringify(question) }),
    headers: { 'Content-Type': 'application/json', 'X-Request-ID': id },
    signal: AbortSignal.timeout(5000)
  });
}
try {
  let ready = false;
  for (let attempt = 0; attempt < 100; attempt++) {
    if (spawnError) throw spawnError;
    if (child.exitCode !== null) throw new Error('Production server exited before becoming ready.');
    try {
      const response = await fetch(origin, { signal: AbortSignal.timeout(500) });
      if (response.ok) { ready = true; break; }
    } catch { /* Wait for the finite-lived child to finish starting. */ }
    await delay(100);
  }
  assert.ok(ready, 'Production server did not become ready within 10 seconds.');
  const home = await request('/');
  assert.equal(home.status, 200);
  const html = await home.text();
  assert.match(html, /FORGE — Clear health information/);
  assert.match(html, /id="question-form"/);
  assert.match(html, /Information, not medical decisions/);
  assert.match(html, /method="POST"/);
  const asset = html.match(/href="([^" ]+\.css)"/);
  assert.ok(asset, 'SSR must include compiled CSS.');
  assert.equal((await request(asset[1])).status, 200);
  assert.equal(home.headers.get('x-request-id'), id);
  assert.equal(home.headers.get('cache-control'), 'no-store');
  const docs = await request('/docs');
  assert.equal(docs.status, 200);
  assert.ok((await docs.json()).paths['/chat']);
  for (const route of ['/chat', '/search']) {
    const refusal = await request(route, { question: 'My friend is unconscious now' });
    assert.equal(refusal.status, 200);
    const data = await refusal.json();
    assert.equal(data.status, 'safety_refusal');
    assert.equal(data.safety_reason, 'urgent');
    assert.deepEqual(data.sources ?? data.hits, []);
    const invalid = await request(route, { question: 'synthetic@example.invalid'.repeat(200) });
    assert.equal(invalid.status, 422);
    assert.ok(!(await invalid.text()).includes('synthetic@example.invalid'));
  }
  const unavailable = await request('/chat', { question: 'What is diabetes?' });
  assert.equal(unavailable.status, 503, 'Missing credentials must fail without a provider call.');
  assert.equal((await request('/sources/not-a-number')).status, 422);
  assert.equal((await request('/health')).status, 200);
  for (const path of ['/.env', '/src/env.ts', '/backend/app/db.py', '/assets/app.mjs']) {
    assert.equal((await request(path)).status, 404, `Private or retired file exposed: ${path}`);
  }
  console.log('Production HTTP smoke passed: SSR, CSS, docs, API contracts, preflight, private-file isolation. No paid API calls.');
} finally {
  if (child.exitCode === null) child.kill();
  await stopped;
}
