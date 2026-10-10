// Check the actual HTTP report against the frontend presentation contract.
// Does not automate a browser or send requests.
import { readFileSync } from 'node:fs';
import assert from 'node:assert/strict';
import { responseView } from '../frontend/public/view-model.mjs';

const reportPath = process.argv[2];
if (!reportPath) throw new Error('Supply a local phase14-e2e JSON report path');
const report = JSON.parse(readFileSync(reportPath, 'utf8'));
for (const c of report.cases) {
  const view = responseView(c.result);
  assert.equal(view.status, c.result.status);
  if (c.expected_reason === 'urgent') assert.ok(view.answer.includes('emergency services now'));
  if (view.status !== 'answered') assert.equal(view.sources.length, 0);
}
console.log(`${report.cases.length} real HTTP responses accepted by frontend view model; no browser automation.`);
