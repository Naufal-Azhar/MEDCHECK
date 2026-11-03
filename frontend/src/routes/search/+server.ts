import type { RequestHandler } from './$types';
import { questionResponse } from '#lib/server/http.ts';

export const POST: RequestHandler = (event) => questionResponse(event, 'search');
