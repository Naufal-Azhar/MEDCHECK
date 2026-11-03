export interface Settings {
  apiKey: string;
  baseUrl: string;
  model: string;
  maxTokens: number;
  timeoutSeconds: number;
}

export interface EvidenceItem {
  citation_id: string;
  chunk_id: number;
  document_id: number;
  title: string;
  source: string;
  source_url: string;
  content: string;
  similarity: number;
}

export interface GroundedContext {
  question: string;
  evidence: EvidenceItem[];
  insufficient_evidence: boolean;
  prompt_context: string;
  insufficiency_reason: string | null;
}

export interface Completion {
  content: string;
  request_id: string;
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  duration_ms: number;
}

export interface AnswerResult {
  status: 'answered' | 'insufficient_evidence' | 'safety_refusal' | 'privacy_refusal' |
    'clarification_needed' | 'invalid_response' | 'provider_error';
  answer: string;
  key_points: string[];
  sources: (Omit<EvidenceItem, 'content' | 'similarity'> & { quote: string })[];
  confidence_or_uncertainty: string;
  safety_note: string;
  usage: (Omit<Completion, 'content'> & {
    calls_attempted: number;
    usage_complete: boolean;
    review_request_id?: string;
  }) | null;
  safety_reason: string | null;
}

export interface ChatMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

export interface SearchHit extends Omit<EvidenceItem, 'citation_id'> {
  chunk_index: number;
  source_id: number;
}

export interface SearchResult {
  request_id: string;
  hits: SearchHit[];
  embedding_ms: number;
  retrieval_ms: number;
  notice: string;
}
