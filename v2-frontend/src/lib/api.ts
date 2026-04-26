// Client API V2 — appels REST + SSE streaming
import type { AskResponse, Module } from './types';

const API_BASE = ''; // relatif (proxy Vite en dev, même domaine en prod)

export interface AskRequest {
  question: string;
  module: Module;
}

/** /api/ask — one-shot JSON (fallback si SSE indispo). */
export async function askOnce(req: AskRequest, signal?: AbortSignal): Promise<AskResponse> {
  const res = await fetch(`${API_BASE}/api/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
    signal,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`HTTP ${res.status} : ${text || res.statusText}`);
  }
  return res.json() as Promise<AskResponse>;
}

/**
 * Événements SSE émis par /api/ask/stream V2.
 *
 * Format wire (V2) — chaque ligne `data: <json>\n\n`, le type est dans le JSON :
 *   data: {"type":"sources","sources":[...],"hors_corpus":false}
 *   data: {"type":"delta","text":"<token>"}
 *   data: {"type":"done"}
 *   data: {"type":"error","message":"...","http_status":503}
 */
export type StreamEvent =
  | { type: 'sources'; sources: AskResponse['sources']; hors_corpus: boolean }
  | { type: 'delta'; text: string }
  | { type: 'done' }
  | { type: 'error'; message: string; http_status?: number };

/**
 * /api/ask/stream — Server-Sent Events.
 * Appelle onEvent à chaque event reçu.
 */
export async function askStream(
  req: AskRequest,
  onEvent: (e: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/ask/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify(req),
    signal,
  });
  if (!res.ok || !res.body) {
    throw new Error(`HTTP ${res.status} : ${res.statusText}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // Découpe par séparateur SSE \n\n
    let sep: number;
    while ((sep = buffer.indexOf('\n\n')) >= 0) {
      const block = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      const ev = parseSSEBlock(block);
      if (ev) onEvent(ev);
    }
  }
}

function parseSSEBlock(block: string): StreamEvent | null {
  // V2 utilise uniquement des lignes `data: <json>` (concaténées si multi-lignes)
  let dataLine = '';
  for (const line of block.split('\n')) {
    if (line.startsWith('data: ')) dataLine += line.slice(6);
    else if (line.startsWith('data:')) dataLine += line.slice(5);
  }
  if (!dataLine) return null;

  try {
    return JSON.parse(dataLine) as StreamEvent;
  } catch {
    return null;
  }
}

/** POST /api/feedback — note 👍 (1) ou 👎 (-1) sur une réponse. */
export interface FeedbackRequest {
  rating: 1 | -1;
  question: string;
  answer: string;
  module: Module;
  comment?: string;
}

export async function postFeedback(req: FeedbackRequest): Promise<void> {
  const res = await fetch(`${API_BASE}/api/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
}
