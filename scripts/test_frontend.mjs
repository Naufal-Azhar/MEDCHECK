import { test } from 'node:test';
import assert from 'node:assert/strict';
import { responseView, inputError, safeSourceUrl } from '../frontend/public/view-model.mjs';

const fixture = () => ({ request_id: 'test-id', status: 'answered', answer: 'Synthetic explanation.',
  key_points: [], confidence_or_uncertainty: 'Limited evidence.', safety_note: 'Not medical advice.',
  sources: [{ citation_id: 'S1', title: 'Synthetic topic', source: 'MedlinePlus',
    source_url: 'https://medlineplus.gov/diabetes.html', quote: 'Synthetic excerpt.' }] });

test('input rejects blank and long questions', () => {
  assert.ok(inputError('  ')); assert.ok(inputError('x'.repeat(2001))); assert.equal(inputError('What is diabetes?'), null);
});
test('answer preserves source vs explanation and supports empty key points', () => {
  const view = responseView(fixture());
  assert.equal(view.answer, 'Synthetic explanation.'); assert.equal(view.sources[0].quote, 'Synthetic excerpt.');
  assert.deepEqual(view.key_points, []);
});
test('refusals and failures never expose arbitrary model content or sources', () => {
  for (const status of ['safety_refusal', 'insufficient_evidence', 'invalid_response', 'provider_error', 'privacy_refusal', 'clarification_needed']) {
    const view = responseView({ ...fixture(), status, answer: 'UNTRUSTED CLAIM' });
    assert.ok(!view.answer.includes('UNTRUSTED')); assert.deepEqual(view.sources, []);
  }
});
test('urgent notice cannot be overwritten by model-authored advice', () => {
  const view = responseView({...fixture(), status: 'safety_refusal', safety_reason: 'urgent', answer: 'Wait until tomorrow.'});
  assert.equal(view.badge, 'Seek urgent help');
  assert.ok(view.answer.includes('emergency services now'));
  assert.ok(!view.answer.includes('tomorrow'));
});
test('malformed answers are not displayed', () => {
  for (const data of [null, {}, {...fixture(), sources: []}, {...fixture(), status: 'unknown'},
    {...fixture(), key_points: 'invalid'}, {...fixture(), sources: [fixture().sources[0], fixture().sources[0]]}]) {
    assert.throws(() => responseView(data));
  }
});
test('only exact official HTTPS source links allowed', () => {
  for (const url of ['javascript:alert(1)', 'http://medlineplus.gov/a.html', 'https://medlineplus.gov.evil.test/a',
    'https://medlineplus.gov@evil.test/a', 'https://evil.test/a', 'https://medlineplus.gov:8443/a']) {
    assert.equal(safeSourceUrl(url), null);
    const f = fixture(); f.sources[0].source_url = url; assert.throws(() => responseView(f));
  }
});
test('HTML remains literal text, never converted to markup by view model', () => {
  const f = fixture(); f.answer = '<img src=x onerror=alert(1)>';
  assert.equal(responseView(f).answer, f.answer);
});

test('source wording is distinguished from AI paraphrase', () => {
  const f = fixture();
  assert.equal(responseView(f).isSourceExcerpt, false);
  f.answer = f.sources[0].quote;
  assert.equal(responseView(f).isSourceExcerpt, true);
});
