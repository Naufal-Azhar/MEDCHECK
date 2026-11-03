// Strict presentation contract. A valid response is NOT proof of medical accuracy.
const notices = {
  insufficient_evidence: ['Not enough evidence', 'The retrieved sources do not provide enough relevant information to answer. Try a specific general health question.'],
  safety_refusal: ['Outside our scope', 'This assistant cannot diagnose, prescribe, or make personal medical decisions. Ask a qualified healthcare professional. If this may be an emergency, contact local emergency services now.'],
  invalid_response: ['Answer withheld', 'The generated response did not pass validation, so it has not been displayed. No automatic retry was made.'],
  provider_error: ['Service unavailable', 'The AI service could not complete the request. No explanation is available. No automatic retry was made.'],
  privacy_refusal: ['Remove personal details', 'Please remove identifying information and medical records, then ask a general health question.'],
  clarification_needed: ['Please clarify', 'Which health topic or term would you like explained? Ask a specific general question without personal details.'],
};
const indonesianNotices = {
  insufficient_evidence: ['Bukti belum cukup', 'Sumber yang ditemukan belum menyediakan informasi relevan yang cukup untuk menjawab. Coba ajukan pertanyaan kesehatan umum yang lebih spesifik.'],
  safety_refusal: ['Di luar cakupan', 'Asisten ini tidak dapat mendiagnosis, meresepkan obat, atau mengambil keputusan medis pribadi. Tanyakan kepada tenaga kesehatan yang berkualifikasi. Jika ini mungkin keadaan darurat, segera hubungi layanan darurat setempat.'],
  invalid_response: ['Jawaban tidak ditampilkan', 'Respons yang dihasilkan tidak lolos validasi, sehingga tidak ditampilkan. Tidak ada percobaan ulang otomatis.'],
  provider_error: ['Layanan tidak tersedia', 'Layanan AI tidak dapat menyelesaikan permintaan. Tidak ada penjelasan yang tersedia. Tidak ada percobaan ulang otomatis.'],
  privacy_refusal: ['Hapus informasi pribadi', 'Hapus informasi pengenal dan rekam medis, lalu ajukan pertanyaan kesehatan umum.'],
  clarification_needed: ['Mohon perjelas', 'Topik atau istilah kesehatan apa yang ingin Anda pahami? Ajukan pertanyaan umum yang spesifik tanpa informasi pribadi.'],
};
const refusalGuidance = {
  en: {
    urgent: ['Seek urgent help', 'Contact local emergency services now. Do not wait for an AI response. This assistant cannot assess the situation or replace emergency care.'],
    uncertainty: 'No validated explanation is available.',
    safety: 'Do not delay professional or emergency care while using this preview.'
  },
  id: {
    urgent: ['Segera cari bantuan darurat', 'Segera hubungi layanan darurat setempat. Jangan menunggu respons AI. Asisten ini tidak dapat menilai situasi atau menggantikan perawatan darurat.'],
    uncertainty: 'Tidak ada penjelasan tervalidasi yang tersedia.',
    safety: 'Jangan tunda bantuan tenaga kesehatan atau layanan darurat saat menggunakan pratinjau ini.'
  }
};
export function safeSourceUrl(value) {
  if (typeof value !== 'string') return null;
  try {
    const u = new URL(value);
    return u.protocol === 'https:' && u.hostname === 'medlineplus.gov' && !u.username && !u.password && !u.port ? u.href : null;
  } catch { return null; }
}
function text(value, limit = 10000) {
  return typeof value === 'string' && value.trim().length > 0 && value.length <= limit;
}
export function responseView(data, locale = 'en') {
  if (!data || typeof data !== 'object' || Array.isArray(data) || !text(data.request_id, 200)
        || typeof data.status !== 'string') throw new Error('Invalid response');
  if (data.status !== 'answered') {
    if (!Object.hasOwn(notices, data.status)) throw new Error('Unknown response status');
    const language = locale === 'id' ? 'id' : 'en';
    const guidance = refusalGuidance[language];
    const [badge, answer] = data.status === 'safety_refusal' && data.safety_reason === 'urgent'
      ? guidance.urgent : (language === 'id' ? indonesianNotices : notices)[data.status];
    return { status: data.status, badge, answer, key_points: [], sources: [], request_id: data.request_id,
      uncertainty: guidance.uncertainty, safety: guidance.safety };
  }
  if (!text(data.answer, 3000) || !text(data.confidence_or_uncertainty, 3000) || !text(data.safety_note, 3000)
      || !Array.isArray(data.key_points) || data.key_points.length > 3 || !Array.from(data.key_points).every(p => text(p, 1000))
      || !Array.isArray(data.sources) || data.sources.length < 1 || data.sources.length > 5) throw new Error('Incomplete response');
  const seen = new Set();
  const sources = Array.from(data.sources).map(s => {
    if (!s || typeof s !== 'object' || Array.isArray(s) || !text(s.citation_id, 50) || seen.has(s.citation_id) || !text(s.title, 500)
        || s.source !== 'MedlinePlus' || !text(s.quote) || !safeSourceUrl(s.source_url)) throw new Error('Invalid source');
    seen.add(s.citation_id);
    return { citation_id: s.citation_id, title: s.title, source: s.source,
          quote: s.quote, source_url: safeSourceUrl(s.source_url) };
  });
  const isSourceExcerpt = sources.some(s => s.quote.includes(data.answer.trim()));
  return { status: data.status, badge: 'Explanation available', answer: data.answer, key_points: [...data.key_points],
    isSourceExcerpt,
    sources, request_id: data.request_id, uncertainty: data.confidence_or_uncertainty, safety: data.safety_note };
}
export function inputError(question) {
  if (!question.trim()) return 'Please enter a general health question in English or Bahasa Indonesia. / Masukkan pertanyaan kesehatan umum dalam bahasa Inggris atau Bahasa Indonesia.';
  if (question.length > 2000) return 'Please shorten your question to 2,000 characters or fewer. / Persingkat pertanyaan Anda menjadi maksimal 2.000 karakter.';
  return null;
}
