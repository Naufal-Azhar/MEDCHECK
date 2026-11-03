import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { inputError, responseView, safeSourceUrl } from '../src/lib/view-model.mjs';
import { detectQuestionLanguage } from '../src/lib/language.ts';

function answered() {
  return {
    request_id: 'test-request',
    status: 'answered',
    answer: 'Diabetes is a condition involving blood glucose.',
    key_points: ['Blood glucose is also called blood sugar.'],
    confidence_or_uncertainty: 'Limited source coverage; this is not medical advice.',
    safety_note: 'Ask a healthcare professional about medical decisions.',
    sources: [{
      citation_id: 'S1',
      title: 'Diabetes',
      source: 'MedlinePlus',
      source_url: 'https://medlineplus.gov/diabetes.html',
      quote: 'Diabetes is a condition involving blood glucose. Blood glucose is also called blood sugar.'
    }]
  };
}

describe('question input contract', () => {
  it.each(['', '   ', '\n\t'])('rejects blank input: %j', (question) => {
    expect(inputError(question)).toBe('Please enter a general health question in English or Bahasa Indonesia. / Masukkan pertanyaan kesehatan umum dalam bahasa Inggris atau Bahasa Indonesia.');
  });

  it('accepts general questions and the exact length boundary without modifying input', () => {
    expect(inputError(' What is diabetes? ')).toBeNull();
    expect(inputError(' Apa itu diabetes? ')).toBeNull();
    expect(inputError('a'.repeat(2000))).toBeNull();
    expect(inputError('a'.repeat(2001))).toBe('Please shorten your question to 2,000 characters or fewer. / Persingkat pertanyaan Anda menjadi maksimal 2.000 karakter.');
    expect(inputError(` ${'a'.repeat(2000)} `)).not.toBeNull();
  });
});

describe('question examples', () => {
  it('offers an Indonesian example that fills the input without submitting', () => {
    const page = readFileSync(new URL('../src/routes/+page.svelte', import.meta.url), 'utf8');
    expect(page).toContain("'Apa itu diabetes?'");
    expect(page).toContain('onclick={() => fillExample(example)}');
    const fillExample = page.match(/function fillExample\(example: string\) \{([\s\S]*?)\n  \}/)?.[1];
    expect(fillExample).toContain('question = example;');
    expect(fillExample).not.toContain('submit(');
    expect(fillExample).not.toContain('fetch(');
  });

  it('selects the locale from the submitted question for response notices', () => {
    const page = readFileSync(new URL('../src/routes/+page.svelte', import.meta.url), 'utf8');
    expect(detectQuestionLanguage('Apa itu diabetes?')).toBe('id');
    expect(detectQuestionLanguage('What is diabetes?')).toBe('en');
    expect(page).toContain("import { detectQuestionLanguage } from '#lib/language.ts'");
    expect(page).toContain('responseView(await response.json(), detectQuestionLanguage(asked))');
  });
});

describe('source URL allowlist', () => {
  it('accepts and normalizes HTTPS links on the exact MedlinePlus host', () => {
    expect(safeSourceUrl('https://MEDLINEPLUS.gov/diabetes.html')).toBe('https://medlineplus.gov/diabetes.html');
    expect(safeSourceUrl('https://medlineplus.gov/')).toBe('https://medlineplus.gov/');
  });

  it.each([
    'http://medlineplus.gov/diabetes.html',
    'https://medlineplus.gov.evil.example/',
    'https://evil.example/medlineplus.gov',
    'https://www.medlineplus.gov/',
    'https://medlineplus.gov./',
    'https://user:password@medlineplus.gov/',
    'https://medlineplus.gov@evil.example/',
    'https://medlineplus.gov:444/',
    '//medlineplus.gov/diabetes.html',
    '/diabetes.html',
    'javascript:alert(1)',
    'data:text/html,<script>alert(1)</script>',
    '', null, undefined, 123, {}, ['https://medlineplus.gov/']
  ])('rejects unsafe or non-string links: %j', (url) => {
    expect(safeSourceUrl(url)).toBeNull();
  });
});

describe('strict explanation presentation contract', () => {
  it('maps a complete answer, exposes only presentation fields and does not mutate it', () => {
    const data = answered();
    const original = structuredClone(data);
    const view = responseView({ ...data, usage: { secret: 'not for display' } });
    expect(view).toEqual({
      status: 'answered', badge: 'Explanation available', answer: data.answer,
      key_points: data.key_points, sources: data.sources, request_id: data.request_id,
      isSourceExcerpt: true, uncertainty: data.confidence_or_uncertainty, safety: data.safety_note
    });
    expect(view).not.toHaveProperty('usage');
    expect(view.key_points).not.toBe(data.key_points);
    expect(view.sources[0]).not.toBe(data.sources[0]);
    expect(data).toEqual(original);
  });

  it('distinguishes selected source wording from an AI explanation, case sensitively', () => {
    expect(responseView({ ...answered(), answer: '  Diabetes is a condition involving blood glucose.  ' }).isSourceExcerpt).toBe(true);
    expect(responseView({ ...answered(), answer: 'An explanation in different words.' }).isSourceExcerpt).toBe(false);
    expect(responseView({ ...answered(), answer: 'diabetes is a condition involving blood glucose.' }).isSourceExcerpt).toBe(false);
  });

  it('preserves markup-like content as plain strings, never treating it as HTML', () => {
    const markup = '<img src=x onerror=alert(1)> & <script>alert(1)</script>';
    const data = answered();
    data.answer = markup;
    data.key_points = [markup];
    data.sources[0].title = markup;
    data.sources[0].quote = markup;
    const view = responseView(data);
    expect(view.answer).toBe(markup);
    expect(view.key_points).toEqual([markup]);
    expect(view.sources[0].title).toBe(markup);
    expect(view.sources[0].quote).toBe(markup);
  });

  it.each([null, undefined, [], 'answered', 1, {}, { request_id: 'x' },
    { request_id: 'x', status: 'unknown' }, { request_id: 'x', status: 'constructor' },
    { request_id: 'x', status: '__proto__' }, { request_id: 'x', status: ['provider_error'] }
  ])('rejects malformed envelopes and unknown statuses: %j', (data) => {
    expect(() => responseView(data)).toThrow();
  });

  it.each([
    ['request_id', ''], ['request_id', ' '.repeat(2)], ['request_id', 'a'.repeat(201)], ['request_id', 4],
    ['answer', ''], ['answer', '  '], ['answer', 'a'.repeat(3001)], ['answer', {}],
    ['confidence_or_uncertainty', null], ['confidence_or_uncertainty', 'a'.repeat(3001)],
    ['safety_note', ''], ['safety_note', 'a'.repeat(3001)],
    ['key_points', null], ['key_points', ['']], ['key_points', [12]],
    ['key_points', ['a'.repeat(1001)]], ['key_points', ['a', 'b', 'c', 'd']],
    ['key_points', Array(1)],
    ['sources', null], ['sources', []], ['sources', [null]], ['sources', Array(1)],
    ['sources', Array.from({ length: 6 }, (_, index) => ({ ...answered().sources[0], citation_id: `S${index}` }))]
  ])('fails closed for invalid field %s: %j', (field, value) => {
    expect(() => responseView({ ...answered(), [field as string]: value })).toThrow();
  });

  it('requires all explanation fields', () => {
    for (const field of Object.keys(answered())) {
      const data: Record<string, unknown> = answered();
      delete data[field];
      expect(() => responseView(data), field).toThrow();
    }
  });

  it.each([
    ['citation_id', ''], ['citation_id', 'a'.repeat(51)], ['title', ''], ['title', 'a'.repeat(501)],
    ['source', 'Other'], ['quote', ''], ['quote', 'a'.repeat(10001)],
    ['source_url', 'https://evil.example/'], ['source_url', ['https://medlineplus.gov/']]
  ])('rejects the entire response for an invalid source %s', (field, value) => {
    const data = answered();
    expect(() => responseView({ ...data, sources: [{ ...data.sources[0], [field as string]: value }] })).toThrow();
  });

  it('rejects duplicate citations rather than rendering conflicting source cards', () => {
    const data = answered();
    expect(() => responseView({ ...data, sources: [data.sources[0], data.sources[0]] })).toThrow();
  });

  it('accepts exact contract boundaries and zero key points', () => {
    const data = answered();
    const sources = Array.from({ length: 5 }, (_, index) => ({
      ...data.sources[0], citation_id: `${index}${'a'.repeat(49)}`, title: 'a'.repeat(500), quote: 'a'.repeat(10000)
    }));
    expect(responseView({
      ...data, request_id: 'a'.repeat(200), answer: 'a'.repeat(3000),
      confidence_or_uncertainty: 'a'.repeat(3000), safety_note: 'a'.repeat(3000),
      key_points: Array(3).fill('a'.repeat(1000)), sources
    }).sources).toHaveLength(5);
    expect(responseView({ ...data, key_points: [] }).key_points).toEqual([]);
  });
});

describe('fixed safety and refusal notices', () => {
  it.each([
    ['insufficient_evidence', 'Bukti belum cukup', 'Sumber yang ditemukan belum menyediakan informasi relevan'],
    ['safety_refusal', 'Di luar cakupan', 'tidak dapat mendiagnosis'],
    ['invalid_response', 'Jawaban tidak ditampilkan', 'tidak lolos validasi'],
    ['provider_error', 'Layanan tidak tersedia', 'Tidak ada percobaan ulang otomatis.'],
    ['privacy_refusal', 'Hapus informasi pribadi', 'Hapus informasi pengenal dan rekam medis'],
    ['clarification_needed', 'Mohon perjelas', 'Topik atau istilah kesehatan apa']
  ])('renders fixed Indonesian %s notice without untrusted response text', (status, badge, answerText) => {
    const view = responseView({
      ...answered(), status, request_id: 'id-request', answer: 'UNTRUSTED ANSWER',
      key_points: ['UNTRUSTED POINT'], confidence_or_uncertainty: 'UNTRUSTED UNCERTAINTY',
      safety_note: 'UNTRUSTED SAFETY', sources: [{ source_url: 'javascript:alert(1)' }]
    }, 'id');
    expect(view.status).toBe(status);
    expect(view.badge).toBe(badge);
    expect(view.answer).toContain(answerText);
    expect(view.uncertainty).toBe('Tidak ada penjelasan tervalidasi yang tersedia.');
    expect(view.safety).toBe('Jangan tunda bantuan tenaga kesehatan atau layanan darurat saat menggunakan pratinjau ini.');
    expect(view.request_id).toBe('id-request');
    expect(view.key_points).toEqual([]);
    expect(view.sources).toEqual([]);
    expect(JSON.stringify(view)).not.toContain('UNTRUSTED');
    expect(JSON.stringify(view)).not.toContain('javascript:');
  });

  it('uses only fixed Indonesian urgent guidance and preserves the request ID', () => {
    const view = responseView({
      ...answered(), request_id: 'id-urgent', status: 'safety_refusal', safety_reason: 'urgent',
      answer: 'UNTRUSTED: wait until tomorrow', safety_note: 'UNTRUSTED SAFETY'
    }, 'id');
    expect(view.badge).toBe('Segera cari bantuan darurat');
    expect(view.answer).toBe('Segera hubungi layanan darurat setempat. Jangan menunggu respons AI. Asisten ini tidak dapat menilai situasi atau menggantikan perawatan darurat.');
    expect(view.request_id).toBe('id-urgent');
    expect(view.sources).toEqual([]);
    expect(JSON.stringify(view)).not.toContain('UNTRUSTED');
  });

  it('keeps answered content unchanged for Indonesian questions', () => {
    expect(responseView(answered(), 'id')).toEqual(responseView(answered()));
  });
  it.each([
    ['insufficient_evidence', 'Not enough evidence'],
    ['safety_refusal', 'Outside our scope'],
    ['invalid_response', 'Answer withheld'],
    ['provider_error', 'Service unavailable'],
    ['privacy_refusal', 'Remove personal details'],
    ['clarification_needed', 'Please clarify']
  ])('renders %s without exposing unvalidated server prose or sources', (status, badge) => {
    const view = responseView({
      ...answered(), status, answer: 'UNTRUSTED ANSWER', key_points: ['UNTRUSTED POINT'],
      confidence_or_uncertainty: 'UNTRUSTED UNCERTAINTY', safety_note: 'UNTRUSTED SAFETY',
      sources: [{ source_url: 'javascript:alert(1)' }]
    });
    expect(view.status).toBe(status);
    expect(view.badge).toBe(badge);
    expect(view.key_points).toEqual([]);
    expect(view.sources).toEqual([]);
    expect(view.uncertainty).toBe('No validated explanation is available.');
    expect(view.safety).toContain('Do not delay professional or emergency care');
    expect(JSON.stringify(view)).not.toContain('UNTRUSTED');
  });

  it('renders urgent safety refusals with immediate emergency guidance', () => {
    const view = responseView({ request_id: 'urgent-test', status: 'safety_refusal', safety_reason: 'urgent' });
    expect(view.badge).toBe('Seek urgent help');
    expect(view.answer).toBe('Contact local emergency services now. Do not wait for an AI response. This assistant cannot assess the situation or replace emergency care.');
    expect(view.sources).toEqual([]);
  });

  it('does not promote unrelated notices to urgent status', () => {
    expect(responseView({ request_id: 'test', status: 'privacy_refusal', safety_reason: 'urgent' }).badge).toBe('Remove personal details');
    expect(responseView({ request_id: 'test', status: 'safety_refusal', safety_reason: 'other' }).badge).toBe('Outside our scope');
  });

  it.each(['', ' ', 'a'.repeat(201), null])('requires a valid reference ID even for refusals: %j', (request_id) => {
    expect(() => responseView({ request_id, status: 'safety_refusal', safety_reason: 'urgent' })).toThrow();
  });
});
