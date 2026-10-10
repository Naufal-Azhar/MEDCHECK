// Strict presentation contract. A valid response is NOT proof of medical accuracy.
const notices = {
  insufficient_evidence: ['Not enough evidence', 'The retrieved sources do not provide enough relevant information to answer. Try a specific general health question.'],
  safety_refusal: ['Outside our scope', 'This assistant cannot diagnose, prescribe, or make personal medical decisions. Ask a qualified healthcare professional. If this may be an emergency, contact local emergency services now.'],
  invalid_response: ['Answer withheld', 'The generated response did not pass validation, so it has not been displayed. No automatic retry was made.'],
  provider_error: ['Service unavailable', 'The AI service could not complete the request. No explanation is available. No automatic retry was made.'],
  privacy_refusal: ['Remove personal details', 'Please remove identifying information and medical records, then ask a general health question.'],
  clarification_needed: ['Please clarify', 'Which health topic or term would you like explained? Ask a specific general question without personal details.'],
};
export function safeSourceUrl(value) {
  try {
    const u = new URL(value);
    return u.protocol === 'https:' && u.hostname === 'medlineplus.gov' && !u.username && !u.password && !u.port ? u.href : null;
  } catch { return null; }
}
function text(value, limit = 10000) {
  return typeof value === 'string' && value.trim().length > 0 && value.length <= limit;
}
export function responseView(data) {
  if (!data || typeof data !== 'object' || !text(data.request_id, 200)) throw new Error('Invalid response');
  if (data.status !== 'answered') {
    if (!Object.hasOwn(notices, data.status)) throw new Error('Unknown response status');
    let [badge, answer] = notices[data.status];
    if (data.status === 'safety_refusal' && data.safety_reason === 'urgent') {
      badge = 'Seek urgent help';
      answer = 'Contact local emergency services now. Do not wait for an AI response. This assistant cannot assess the situation or replace emergency care.';
    }
    return { status: data.status, badge, answer, key_points: [], sources: [], request_id: data.request_id,
      uncertainty: 'No validated explanation is available.', safety: 'Do not delay professional or emergency care while using this preview.' };
  }
  if (!text(data.answer, 3000) || !text(data.confidence_or_uncertainty, 3000) || !text(data.safety_note, 3000)
      || !Array.isArray(data.key_points) || data.key_points.length > 3 || !data.key_points.every(p => text(p, 1000))
      || !Array.isArray(data.sources) || data.sources.length < 1 || data.sources.length > 5) throw new Error('Incomplete response');
  const seen = new Set();
  const sources = data.sources.map(s => {
    if (!s || !text(s.citation_id, 50) || seen.has(s.citation_id) || !text(s.title, 500)
        || s.source !== 'MedlinePlus' || !text(s.quote) || !safeSourceUrl(s.source_url)) throw new Error('Invalid source');
    seen.add(s.citation_id);
    return { ...s, source_url: safeSourceUrl(s.source_url) };
  });
  const isSourceExcerpt = sources.some(s => s.quote.includes(data.answer.trim()));
  return { status: data.status, badge: 'Explanation available', answer: data.answer, key_points: data.key_points,
    isSourceExcerpt,
    sources, request_id: data.request_id, uncertainty: data.confidence_or_uncertainty, safety: data.safety_note };
}
export function inputError(question) {
  if (!question.trim()) return 'Please enter a general health question in English.';
  if (question.length > 2000) return 'Please shorten your question to 2,000 characters or fewer.';
  return null;
}
