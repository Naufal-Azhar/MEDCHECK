import type { RequestHandler } from './$types';
import { healthResponse } from '#lib/server/http.ts';

export const GET: RequestHandler = healthResponse;
