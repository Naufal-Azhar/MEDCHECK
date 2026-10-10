import { responseView, inputError } from './view-model.mjs';

const $ = id => document.getElementById(id);
const form = $('question-form');
const question = $('question');
const controls = [question, $('submit-button'), ...document.querySelectorAll('[data-question]')];
let busy = false;

function count() { $('character-count').textContent = `${question.value.length.toLocaleString('en-US')} / 2,000 characters`; }
question.addEventListener('input', count);
for (const button of document.querySelectorAll('[data-question]')) {
  button.addEventListener('click', () => { question.value = button.dataset.question; count(); question.focus(); });
}
function clearResult() {
  $('result').hidden = true;
  $('sources').replaceChildren();
  $('key-points').replaceChildren();
  for (const id of ['answer', 'asked-question', 'uncertainty-text', 'safety-text', 'request-id']) $(id).textContent = '';
  $('error').hidden = true;
  $('error').textContent = '';
}
function render(view, asked) {
  $('response-badge').textContent = view.badge;
  $('asked-question').textContent = `You asked: ${asked}`;
  $('explanation-label').textContent = view.status === 'answered'
    ? view.isSourceExcerpt ? 'Source wording · selected by AI' : 'AI explanation · not a direct quote'
    : 'Assistant notice · no medical answer';
  $('answer').textContent = view.answer;
  $('uncertainty-text').textContent = view.uncertainty;
  $('safety-text').textContent = view.safety;
  $('request-id').textContent = `Reference ID: ${view.request_id}`;
  for (const point of view.key_points) {
    const li = document.createElement('li'); li.textContent = point; $('key-points').append(li);
  }
  $('key-points-section').hidden = view.key_points.length === 0;
  for (const source of view.sources) {
    const article = document.createElement('article'); article.className = 'source-card';
    const label = document.createElement('p'); label.className = 'eyebrow'; label.textContent = `[${source.citation_id}] ${source.source} · Source text`;
    const link = document.createElement('a'); link.href = source.source_url; link.target = '_blank'; link.rel = 'noopener noreferrer'; link.referrerPolicy = 'no-referrer';
    link.textContent = `${source.title} ↗`; link.setAttribute('aria-label', `${source.title} (opens in a new tab)`);
    const quote = document.createElement('blockquote'); quote.textContent = source.quote;
    article.append(label, link, quote); $('sources').append(article);
  }
  $('sources-section').hidden = view.sources.length === 0;
  $('result').hidden = false;
}

form.addEventListener('submit', async event => {
  event.preventDefault();
  if (busy) return;
  clearResult();
  const asked = question.value.trim();
  const error = inputError(question.value);
  if (error) { $('error').textContent = error; $('error').hidden = false; question.focus(); return; }
  busy = true;
  controls.forEach(control => { control.disabled = true; });
  $('empty-state').hidden = true;
  $('response-region').setAttribute('aria-busy', 'true');
  $('response-badge').textContent = 'Working';
  $('progress').textContent = 'Finding evidence and preparing an explanation. This may take a little while.';
  const controller = new AbortController();
  // Embedding + generation + review can each take up to 60 seconds. No retries.
  const timeout = setTimeout(() => controller.abort(), 210000);
  try {
    const response = await fetch('/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: asked }), signal: controller.signal, cache: 'no-store' });
    if (!response.ok) {
      const message = response.status === 422 ? 'The question could not be accepted. Try a shorter general health question.'
        : response.status === 429 ? 'Too many requests. Wait before submitting again.'
          : 'The service is unavailable. Check the backend connection before submitting again.';
      throw new Error(message);
    }
    let view;
    try { view = responseView(await response.json()); }
    catch { throw new Error('The response could not be safely displayed. No explanation is shown.'); }
    render(view, asked);
  } catch (err) {
    $('response-badge').textContent = 'Request not completed';
    $('error').textContent = err.name === 'AbortError'
      ? 'The wait timed out. The server may still be processing this request and API charges may still apply. No automatic retry was made.'
      : err instanceof TypeError ? 'Could not reach the server. Check your connection. No automatic retry was made.' : err.message;
    $('error').hidden = false;
  } finally {
    clearTimeout(timeout);
    busy = false;
    controls.forEach(control => { control.disabled = false; });
    $('progress').textContent = '';
    $('response-region').setAttribute('aria-busy', 'false');
    $('response-title').focus();
  }
});
