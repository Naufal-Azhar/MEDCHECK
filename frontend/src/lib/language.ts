/** Lightweight question-language hint; not a general-purpose language detector. */
export function detectQuestionLanguage(question: string): 'en' | 'id' {
  const text = question.normalize('NFKC').toLowerCase().replace(/\p{Cf}/gu, '').replace(/\s+/gu, ' ');
  // Require Indonesian question/request phrasing, not shared medical vocabulary.
  const markers = /(?:^|[^\p{L}\p{N}_])(?:apa\s+(?:itu|penyebab|kegunaan|gejala|fungsi|yang|saja|dosis|penyakit|manfaat)|apakah|bagaimana|jelaskan|mengapa|kenapa|haruskah|bolehkah|berapa\s+(?:dosis|banyak)|saya|aku|anakku|anak\s+saya|ibu\s+saya|ayah\s+saya|teman\s+saya|pasien\s+ini|nomor\s+rekam\s+medis|nik\s*[:#=]|abaikan\s+aturan|buat\s+sumber\s+palsu|bocorkan\s+kunci\s+api)(?=$|[^\p{L}\p{N}_])/u;
  // "Apa diabetes?" begins with a question word; "diabetes itu apa?" ends with one.
  const openQuestion = /^\s*apa\s+[\p{L}][\p{L}\p{N}_-]*(?=$|[^\p{L}\p{N}_])/u;
  const reversedQuestion = /(?:^|[^\p{L}\p{N}_])itu\s+apa(?=\s*[?!.,;:]?\s*$)/u;
  return markers.test(text) || openQuestion.test(text) || reversedQuestion.test(text) ? 'id' : 'en';
}
