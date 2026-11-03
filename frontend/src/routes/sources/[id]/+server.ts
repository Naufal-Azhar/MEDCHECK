import type { RequestHandler } from './$types';
import { sourceResponse } from '#lib/server/http.ts';

export const GET: RequestHandler = (event) => sourceResponse(event, event.params.id);
