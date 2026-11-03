import type { RequestHandler } from './$types';
import { apiJson, requestId } from '#lib/server/http.ts';

const ref = (name: string) => ({ $ref: `#/components/schemas/${name}` });
const json = (schema: unknown) => ({ 'application/json': { schema } });
const errorResponses = {
  '422': { description: 'Invalid request (input is never echoed)', content: json(ref('Error')) },
  '503': { description: 'Service unavailable', content: json(ref('Error')) },
};
const questionOperation = (schema: string) => ({
  requestBody: { required: true, content: json(ref('QuestionRequest')) },
  responses: { '200': { description: 'Result, including safe abstentions', content: json(ref(schema)) }, ...errorResponses },
});
const text = { type: 'string' };
const strings = { type: 'array', items: text };
const id = { type: 'integer', minimum: 1 };
const nullableText = { type: ['string', 'null'] };
const attribution = { citation_id: text, chunk_id: id, document_id: id, title: text, source: text, source_url: text };

export const GET: RequestHandler = (event) => apiJson({
  openapi: '3.1.0',
  info: { title: 'ForgeHacks Healthcare Information Assistant', version: '0.1.0',
    description: 'Grounded healthcare information retrieval and explanation API. Educational information only.' },
  paths: {
    '/chat': { post: questionOperation('ChatResponse') },
    '/search': { post: questionOperation('SearchResponse') },
    '/health': { get: { responses: { '200': { description: 'Database availability', content: json({
      type: 'object', properties: { status: { enum: ['ok', 'degraded'] }, service: text, database: text },
    }) } } } },
    '/sources/{id}': { get: {
      parameters: [{ name: 'id', in: 'path', required: true, schema: id }],
      responses: { '200': { description: 'Source attribution', content: json(ref('SourceResponse')) },
        '404': { description: 'Source not found', content: json(ref('Error')) }, ...errorResponses },
    } },
    '/docs': { get: { responses: { '200': { description: 'This OpenAPI document' } } } },
  },
  components: { schemas: {
    QuestionRequest: { type: 'object', required: ['question'], properties: {
      question: { type: 'string', minLength: 1, maxLength: 2000 }, top_k: { type: 'integer', minimum: 1, maximum: 20, default: 5 },
    } },
    Error: { type: 'object', required: ['detail', 'request_id'], properties: { detail: text, request_id: { type: 'string', format: 'uuid' } } },
    SourceResponse: { type: 'object', properties: { id, name: text, base_url: text, authority_level: text, metadata: { type: 'object' } } },
    ChatSource: { type: 'object', properties: { ...attribution, quote: text } },
    SearchHit: { type: 'object', properties: { ...attribution, chunk_index: { type: 'integer' }, content: text, similarity: { type: 'number' } } },
    ChatResponse: { type: 'object', properties: { request_id: text, status: text, answer: text, key_points: strings,
      sources: { type: 'array', items: ref('ChatSource') }, confidence_or_uncertainty: text, safety_note: text,
      usage: { type: ['object', 'null'] }, safety_reason: nullableText } },
    SearchResponse: { type: 'object', properties: { request_id: text, question: text, hits: { type: 'array', items: ref('SearchHit') },
      embedding_ms: { type: 'number' }, retrieval_ms: { type: 'number' }, notice: text, status: text, safety_reason: nullableText } },
  } },
}, requestId(event.locals.requestId));
