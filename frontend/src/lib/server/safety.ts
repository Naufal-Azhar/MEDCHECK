import { detectQuestionLanguage } from '../language';

/** Conservative local routing, not exhaustive triage or proof that unmatched input is safe. */
export interface SafetyDecision {
  status: 'safety_refusal' | 'privacy_refusal' | 'clarification_needed';
  reason: 'urgent' | 'instruction_override' | 'personal_identifiers' | 'personal_medical_decision' | 'ambiguous';
  message: string;
}

/** Default Unicode case folding, including expansions; unlike locale-sensitive lowercasing. */
export function casefold(text: string): string {
  return Array.from(text, (character) => {
    const code = character.codePointAt(0)!;
    // Default folding preserves dotless i and folds Cherokee to uppercase.
    if (character === '\u0131') return character;
    if ((code >= 0x13a0 && code <= 0x13f5) || (code >= 0x13f8 && code <= 0x13fd) ||
        (code >= 0xab70 && code <= 0xabbf)) return character.toUpperCase();
    return character.toUpperCase().toLowerCase().replace(/ß/g, 'ss').replace(/ς/g, 'σ');
  }).join('');
}

export function normalize(text: string): string {
  return casefold(text.normalize('NFKC')).replace(/’/g, "'")
    .replace(/\p{Cf}/gu, '').replace(/[\s\u0085\u001c-\u001f]+/gu, ' ').trim();
}

// JS \\b is ASCII-only even with /u; Python boundaries include Unicode letters/numbers.
function pythonPattern(pattern: RegExp): RegExp {
  const word = '[\\p{L}\\p{N}_]';
  const boundary = `(?:(?<!${word})(?=${word})|(?<=${word})(?!${word}))`;
  return new RegExp(pattern.source.replace(/\\b/g, boundary), pattern.flags);
}

function matches(pattern: RegExp, text: string): boolean {
  return pythonPattern(pattern).test(text);
}

function personalDecision(input: string): boolean {
  // Remove request markers only, not subsequent personal case descriptions.
  const text = input.replace(pythonPattern(/\bto me\b/gu), '')
    .replace(pythonPattern(/\b(?:tell|show|teach) me\b/gu), 'explain')
    .replace(pythonPattern(/\b(?:can|could|would) you help me (?:understand|learn about)\b/gu), 'explain')
    .replace(pythonPattern(/\b(?:jelaskan|terangkan) (?:kepada|untuk) saya\b/gu), 'jelaskan');
  const personal = /\b(i|i'm|i've|me|my|mine|we|our|he|she|his|her|they|their|patient|someone|saya|aku|kami|dia|pasien)\b/u;
  const medical = /\b(symptoms?|diabet[\p{L}\p{N}_]*|insulin|medicat[\p{L}\p{N}_]*|medicin[\p{L}\p{N}_]*|disease|condition|pain|thirst[\p{L}\p{N}_]*|urina[\p{L}\p{N}_]*|breath[\p{L}\p{N}_]*|fever|dose|dosage|pills?|tablets?|metformin|sick|ill|bleed[\p{L}\p{N}_]*|dizz[\p{L}\p{N}_]*|vomit[\p{L}\p{N}_]*|rash|numb[\p{L}\p{N}_]*|pregnan[\p{L}\p{N}_]*|chest|doctor|treatment|cancer|blood|antibiotic[\p{L}\p{N}_]*|gejala|obat|dosis|tablet|penyakit|sakit|nyeri|demam|pusing|mual|muntah|haus|sesak|napas|berdarah|hamil|gula darah|hasil tes|hasil lab|pengobatan|antibiotik)\b/u;
  if (matches(personal, text) && matches(medical, text)) return true;
  if ([
    /\bdiagnos(?:e|ing)\b/u, /\bprescrib(?:e|ing)\b/u,
    /\b(?:what|which)\s+(?:dose|dosage|units|mg|tablets|pills)\b/u,
    /\b(?:how much|how many)\b.{0,100}\b(?:dose|dosage|units|mg|tablets|pills)\b/u,
    /\b(?:should|can|must)\b.{0,60}\b(?:take|inject|stop|increase|decrease|double|wait)\b/u,
    /\b(?:tell|give|recommend|calculate)\b.{0,80}\b(?:treatment|medicine|medication|dose|dosage)\b/u,
    /\b(?:age[d]?\s*\p{Nd}+|\p{Nd}+\s*(?:years? old|year-old|kg))\b.{0,120}\b(?:symptoms?|dose|insulin|pain|diabetes)\b/u,
    /\b(?:diagnosiskan|diagnosakan|resepkan|obati)\b/u,
    /\b(?:berapa|tentukan|hitung|sarankan)\b.{0,70}\b(?:dosis|tablet|unit|mg|obat)\b/u,
    /\b(?:haruskah|bolehkah|perlukah)\b.{0,80}\b(?:minum|suntik|pakai|hentikan|berhenti|tambah|kurangi|ganti|tunggu|periksa|ke dokter)\b/u,
    /\b(?:hentikan|berhenti|gandakan|tambah|kurangi|ganti)\b.{0,50}\b(?:obat|dosis|insulin|metformin|antibiotik)\b/u,
    /\b(?:apa|apakah)\b.{0,50}\b(?:penyakit|diagnosis)\b.{0,40}\b(?:saya|dia|ini)\b/u,
  ].some((pattern) => matches(pattern, text))) return true;
  return matches(/\b(chest pain|trouble breathing|difficulty breathing|can't breathe|cannot breathe|unconscious|overdose|severe bleeding)\b/u, text) &&
    matches(/\b(now|right now|severe|suddenly|help|emergency|wait|tomorrow)\b/u, text);
}

export function instructionAttack(input: string): boolean {
  const text = normalize(input);
  return [
    /\b(ignore|override|bypass|disregard)\b.{0,80}\b(instructions?|rules?|safety|system|guardrails?)\b/u,
    /\b(reveal|print|show|repeat)\b.{0,60}\b(system prompt|api key|secret|credentials?)\b/u,
    /\b(invent|fabricate|fake)\b.{0,50}\b(citations?|sources?|evidence)\b/u,
    /\b(pretend|act|roleplay)\b.{0,50}\b(doctor|physician|unrestricted)\b/u,
    /\b(?:abaikan|langgar|lewati)\b.{0,80}\b(?:aturan|instruksi|keselamatan|sistem)\b/u,
    /\b(?:bocorkan|ungkapkan|tampilkan)\b.{0,60}\b(?:kunci api|api key|rahasia|kata sandi|prompt sistem)\b/u,
    /\b(?:buat|karang|palsukan)\b.{0,50}\b(?:sumber palsu|sitasi palsu|bukti palsu)\b/u,
    /\b(?:berpura-pura|berperan)\b.{0,50}\b(?:dokter|tanpa batasan)\b/u,
    /<\|(?:system|im_start|endoftext)\|>|\[inst\]/u,
  ].some((pattern) => matches(pattern, text));
}

export function screenQuestion(question: string): SafetyDecision | null {
  const text = normalize(question);
  const language = detectQuestionLanguage(question);
  const distress = matches(/\b(chest pain|trouble breathing|difficulty breathing|can't breathe|cannot breathe|not breathing|unconscious|unresponsive|overdose|severe bleeding|nyeri dada|sakit dada|sesak napas|sesak nafas|sulit bernapas|tidak bisa bernapas|tidak bernapas|pingsan|tidak sadar|perdarahan hebat|pendarahan hebat|overdosis)\b/u, text);
  const immediate = matches(/\b(now|severe|suddenly|help|wait|tomorrow|i|my|he|she|child|friend|sekarang|parah|tiba-tiba|tolong|tunggu|besok|saya|aku|dia|anak|teman|ibu|ayah)\b/u, text);
  if ((distress && immediate) || matches(/\b(i (?:want|plan|intend) to (?:kill|hurt) myself|i took an overdose|(?:saya|aku) (?:ingin|mau|berencana) (?:bunuh diri|menyakiti diri)|(?:saya|aku) (?:minum|mengalami) overdosis)\b/u, text)) {
    return { status: 'safety_refusal', reason: 'urgent', message: language === 'id' ? 'Ini mungkin memerlukan pertolongan darurat. Hubungi layanan darurat setempat sekarang. Jangan menunggu jawaban AI. Asisten ini tidak dapat menilai kondisi Anda atau menggantikan perawatan darurat.' : 'This could require urgent care. Contact local emergency services now. Do not wait for an AI response. This assistant cannot assess the situation or replace emergency care.' };
  }
  if (instructionAttack(text)) {
    return { status: 'safety_refusal', reason: 'instruction_override', message: language === 'id' ? 'Saya dapat menjelaskan informasi kesehatan berdasarkan sumber, tetapi tidak dapat mengabaikan aturan keselamatan, membocorkan rahasia, atau mengarang bukti. Ajukan pertanyaan edukasi umum.' : 'I can explain source-based health information, but cannot bypass safety rules, reveal secrets, or invent evidence. Please ask a general educational question.' };
  }
  if (matches(/[\p{L}\p{N}_.+-]+@[\p{L}\p{N}_.-]+\.[a-z]{2,}|\b(?:mrn|patient id|medical record number|date of birth|dob|nomor rekam medis|no\.? rekam medis|nik)\s*[:#=]|\bnik\s+\p{Nd}{16}\b|\b\p{Nd}{3}-\p{Nd}{2}-\p{Nd}{4}\b/u, text)) {
    return { status: 'privacy_refusal', reason: 'personal_identifiers', message: language === 'id' ? 'Hapus informasi pengenal dan rekam medis, lalu ajukan pertanyaan kesehatan umum. Asisten ini hanya untuk informasi edukasi publik.' : 'Please remove identifying information and medical records, then ask a general health question. This assistant is for public educational information.' };
  }
  if (personalDecision(text) || [
    /\b(?:do|could|might|can) i have\b/u,
    /\b(?:what|which) (?:disease|condition) (?:is this|do i have)\b/u,
    /\b(?:my|his|her|your) (?:lab|test|scan|results?|symptoms?)\b/u,
    /\b(?:start|stop|double|halve|increase|decrease|switch)\b.{0,50}\b(?:dose|medication|insulin|metformin|antibiotics?)\b/u,
    /\b(?:hasil (?:lab|tes|pemeriksaan)|gejala) (?:saya|anak saya|ibu saya|ayah saya|dia)\b/u,
    /\b(?:apakah|apa)\b.{0,50}\b(?:saya|anak saya|dia)\b.{0,50}\b(?:menderita|terkena|punya)\b/u,
  ].some((pattern) => matches(pattern, text))) {
    return { status: 'safety_refusal', reason: 'personal_medical_decision', message: language === 'id' ? 'Saya tidak dapat mendiagnosis, meresepkan, menafsirkan gejala atau hasil tes seseorang, atau menyarankan dosis pribadi. Tanyakan kepada tenaga kesehatan yang kompeten. Anda dapat bertanya tentang istilah kesehatan secara umum.' : "I cannot diagnose, prescribe, interpret a person's symptoms or tests, or recommend a personal dose. Ask a qualified healthcare professional. You can ask about general health terminology instead." };
  }
  if (matches(/^(?:is (?:it|this|that) safe|what (?:is|does) (?:it|this|that)(?: mean)?|help|what should i do|apakah (?:ini|itu) aman|apa (?:itu|ini)\??|bagaimana|tolong|tolong bantu|saya harus bagaimana)[?.! ]*$/u, text)) {
    return { status: 'clarification_needed', reason: 'ambiguous', message: language === 'id' ? 'Topik atau istilah kesehatan apa yang ingin Anda ketahui? Ajukan pertanyaan umum yang spesifik tanpa detail pribadi.' : 'Which health topic or term would you like explained? Please ask a specific general question without personal details.' };
  }
  return null;
}

export function unsafeOutput(input: string): boolean {
  const text = normalize(input);
  return instructionAttack(text) || matches(/(?<!if )\byou (?:definitely |certainly )?(?:have|suffer from)\b|\b(?:take|inject|swallow)\s+\p{Nd}|\b(?:stop|double|increase|decrease) your\b|\b(?:do not|don't|no need to) (?:call|seek|go to)\b|\bwait until tomorrow\b|\b(?:anda|kamu|saya) (?:pasti )?(?:menderita|mengidap|terkena)\b|\b(?:minum|suntik|suntikkan|telan)\s+\p{Nd}+\s*(?:mg|unit|tablet|pil|obat)?\b|\b(?:hentikan|gandakan|tambah|kurangi)\s+(?:obat|dosis|insulin)(?:mu| anda| kamu)?\b|\b(?:jangan|tidak perlu|tidak usah)\s+(?:(?:pergi|hubungi|cari|datang)\s+)?(?:ke )?(?:dokter|rumah sakit|layanan darurat|pertolongan medis)\b|\b(?:tunda|tunggu)\b.{0,50}\b(?:besok|lusa|perawatan|pertolongan medis|ke dokter)\b|\b(?:kunci api|api key|secret|rahasia)\s*[:=]\s*\S+/u, text);
}
