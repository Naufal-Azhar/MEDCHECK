export type ResponseStatus = 'answered' | 'insufficient_evidence' | 'safety_refusal'
  | 'invalid_response' | 'provider_error' | 'privacy_refusal' | 'clarification_needed';

export interface SourceView {
  citation_id: string;
  title: string;
  source: 'MedlinePlus';
  quote: string;
  source_url: string;
}

export interface ResponseView {
  status: ResponseStatus;
  badge: string;
  answer: string;
  key_points: string[];
  sources: SourceView[];
  request_id: string;
  isSourceExcerpt?: boolean;
  uncertainty: string;
  safety: string;
}

export function safeSourceUrl(value: unknown): string | null;
export function responseView(data: unknown, locale?: 'en' | 'id'): ResponseView;
export function inputError(question: string): string | null;
