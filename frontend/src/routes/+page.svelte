<script lang="ts">
  import { onDestroy, tick } from 'svelte';
  import { inputError, responseView, type ResponseView } from '#lib/view-model.mjs';
  import { detectQuestionLanguage } from '#lib/language.ts';

  const examples = ['What is diabetes?', 'Apa itu diabetes?', 'What is dehydration?', 'What are antibiotics used for?'];
  let question = $state('');
  let asked = $state('');
  let busy = $state(false);
  let attempted = $state(false);
  let error = $state('');
  let view = $state<ResponseView | null>(null);
  let questionInput: HTMLTextAreaElement | undefined;
  let responseTitle: HTMLHeadingElement | undefined;
  let controller: AbortController | undefined;
  let timeout: ReturnType<typeof setTimeout> | undefined;
  let destroyed = false;

  const characterCount = $derived(`${question.length.toLocaleString('en-US')} / 2,000 characters`);
  const badge = $derived(busy ? 'Working' : view?.badge ?? (attempted ? 'Request not completed' : 'Ready when you are'));
  const explanationLabel = $derived(view?.status === 'answered'
    ? view.isSourceExcerpt ? 'Source wording · selected by AI' : 'AI explanation · not a direct quote'
    : 'Assistant notice · no medical answer');

  onDestroy(() => {
    destroyed = true;
    clearTimeout(timeout);
    controller?.abort();
  });

  function fillExample(example: string) {
    if (busy) return;
    question = example;
    questionInput?.focus();
  }

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    if (busy) return;
    view = null;
    error = '';
    const validationError = inputError(question);
    if (validationError) {
      error = validationError;
      questionInput?.focus();
      return;
    }
    asked = question.trim();
    attempted = true;
    busy = true;
    const requestController = new AbortController();
    controller = requestController;
    // Embedding, generation and review may each take 60 seconds. Never retry.
    timeout = setTimeout(() => requestController.abort(), 210_000);
    try {
      const response = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: asked }),
        signal: requestController.signal,
        cache: 'no-store'
      });
      if (!response.ok) {
        throw new Error(response.status === 422
          ? 'The question could not be accepted. Try a shorter general health question.'
          : response.status === 429
            ? 'Too many requests. Wait before submitting again.'
            : 'The service is unavailable. Check the backend connection before submitting again.');
      }
      let result: ResponseView;
      try {
        result = responseView(await response.json(), detectQuestionLanguage(asked));
      } catch {
        throw new Error('The response could not be safely displayed. No explanation is shown.');
      }
      if (!destroyed) view = result;
    } catch (err: unknown) {
      if (!destroyed) {
        error = requestController.signal.aborted
          ? 'The wait timed out. The server may still be processing this request and API charges may still apply. No automatic retry was made.'
          : err instanceof TypeError
            ? 'Could not reach the server. Check your connection. No automatic retry was made.'
            : err instanceof Error ? err.message : 'The request could not be completed. No automatic retry was made.';
      }
    } finally {
      clearTimeout(timeout);
      controller = undefined;
      if (!destroyed) {
        busy = false;
        await tick();
        if (!destroyed) responseTitle?.focus();
      }
    }
  }
</script>

<svelte:head>
  <title>FORGE — Clear health information</title>
  <meta name="description" content="Explore healthcare information with plain-language explanations and MedlinePlus sources." />
</svelte:head>

<a class="skip-link" href="#question">Skip to question</a>
<header class="site-header">
  <a class="brand" href="/" aria-label="FORGE home"><span class="brand-icon" aria-hidden="true">F</span> FORGE <span class="brand-tag">Health information</span></a>
  <span class="demo-badge">Development preview</span>
</header>
<main>
  <section class="intro" aria-labelledby="intro-title">
    <p class="eyebrow">Understand more. Start with a source.</p>
    <h1 id="intro-title">Health information,<br /><span>made clearer.</span></h1>
    <p class="intro-copy">Ask a general health question in English or Bahasa Indonesia. Explore a plain-language explanation with the source excerpts behind it.</p>
    <div class="steps" aria-label="How it works"><span>01 &nbsp; Ask a question</span><span>02 &nbsp; Find evidence</span><span>03 &nbsp; Explain &amp; cite</span></div>
  </section>

  <div class="workspace">
    <section class="card question-card" aria-labelledby="ask-title">
      <p class="eyebrow">Your starting point</p>
      <h2 id="ask-title">What would you like to understand?</h2>
      <form id="question-form" method="POST" autocomplete="off" onsubmit={submit}>
        <label for="question">General health question <span class="label-hint">English or Bahasa Indonesia</span></label>
        <textarea bind:this={questionInput} bind:value={question} disabled={busy} id="question" name="question" rows="5" maxlength="2000" required placeholder="For example: What is diabetes?" aria-describedby="privacy-note character-count"></textarea>
        <div class="input-meta"><span id="character-count">{characterCount}</span></div>
        <p id="privacy-note" class="helper">Do not include names, contact details, medical records, or personal symptoms. Questions and retrieved evidence are processed by Featherless AI. Source excerpts may remain in English.</p>
        <button id="submit-button" class="primary" type="submit" disabled={busy}>Find an explanation <span aria-hidden="true">→</span></button>
      </form>
      <fieldset class="examples" disabled={busy}>
        <legend>Not sure where to start?</legend>
        {#each examples as example}
          <button type="button" data-question={example} disabled={busy} onclick={() => fillExample(example)}>{example}</button>
        {/each}
      </fieldset>
      <p class="helper">Examples only fill the input. Submitting makes API requests that may use project credits. No automatic retries.</p>
    </section>

    <section class="card answer-card" aria-labelledby="response-title">
      <div class="section-top"><h2 id="response-title" tabindex="-1" bind:this={responseTitle}>Your explanation</h2><span id="response-badge" class="badge">{badge}</span></div>
      <!-- Keep the live status outside the busy region so loading is announced immediately. -->
      <p id="progress" role="status" aria-live="polite">{busy ? 'Finding evidence and preparing an explanation. This may take a little while.' : ''}</p>
      <p id="error" class="error" role="alert" hidden={!error}>{error}</p>
      <div id="response-region" aria-busy={busy}>
        {#if !attempted && !busy && !view}
          <div id="empty-state" class="empty-state">
            <div class="empty-icon" aria-hidden="true">≡</div>
            <h3>A clearer starting point</h3>
            <p>Your explanation and source excerpts will appear here. If the evidence is insufficient, the assistant should say so rather than guess.</p>
          </div>
        {/if}
        {#if view}
          <div id="result">
            <p id="asked-question" class="asked-question">You asked: {asked}</p>
            <p id="explanation-label" class="eyebrow">{explanationLabel}</p>
            <p id="answer" class="answer-text">{view.answer}</p>
            {#if view.key_points.length > 0}
              <section id="key-points-section" aria-labelledby="key-points-title">
                <h3 id="key-points-title">Key points</h3>
                <ul id="key-points">{#each view.key_points as point}<li>{point}</li>{/each}</ul>
              </section>
            {/if}
            <aside class="uncertainty" aria-labelledby="uncertainty-title">
              <h3 id="uncertainty-title">What to keep in mind</h3>
              <p id="uncertainty-text">{view.uncertainty}</p><p id="safety-text">{view.safety}</p>
            </aside>
            {#if view.sources.length > 0}
              <section id="sources-section" aria-labelledby="sources-title">
                <h3 id="sources-title">Source excerpts</h3>
                <p class="helper">Quoted source text is separate from the AI explanation. A citation alone does not verify every claim.</p>
                <div id="sources">
                  {#each view.sources as source (source.citation_id)}
                    <article class="source-card">
                      <p class="eyebrow">[{source.citation_id}] {source.source} · Source text</p>
                      <a href={source.source_url} target="_blank" rel="noopener noreferrer" referrerpolicy="no-referrer" aria-label={`${source.title} (opens in a new tab)`}>{source.title} ↗</a>
                      <blockquote>{source.quote}</blockquote>
                    </article>
                  {/each}
                </div>
              </section>
            {/if}
            <p id="request-id" class="request-id">Reference ID: {view.request_id}</p>
          </div>
        {/if}
      </div>
    </section>
  </div>

  <aside class="safety-banner" aria-labelledby="safety-heading">
    <strong id="safety-heading">Information, not medical decisions.</strong>
    <p>This preview can make mistakes and has limited source coverage. It does not diagnose, prescribe, or replace a healthcare professional. If this may be an emergency, contact local emergency services now. Do not wait for an AI response.</p>
  </aside>
</main>
<footer><span>FORGE · ForgeHacks 2026</span><span>Source information from MedlinePlus.gov · No endorsement implied</span></footer>
