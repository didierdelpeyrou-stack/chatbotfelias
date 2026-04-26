// Client API V2 — appels REST + SSE streaming
import type {
  Acteur,
  AskResponse,
  FichesMetiersResponse,
  Mode,
  Module,
  OrientationDetail,
  OrientationSummary,
  ProfileExtras,
  RegionInfo,
  UserProfile,
} from './types';

const API_BASE = ''; // relatif (proxy Vite en dev, même domaine en prod)

export interface AskRequest {
  question: string;
  module: Module;
  mode?: string | null;          // Sprint 4.6 F1   — id de mode optionnel
  profile?: string | null;       // Sprint 4.6 F1.5 — id de profil utilisateur optionnel
  profile_extras?: ProfileExtras | null;  // Sprint 4.6 — caractéristiques structure
}

/** GET /api/modes — liste des modes disponibles (filtrable par module). */
export async function fetchModes(module?: Module): Promise<Mode[]> {
  const url = module ? `${API_BASE}/api/modes?module=${module}` : `${API_BASE}/api/modes`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const body = await res.json() as { modes: Mode[] };
  return body.modes;
}

/** Sprint 4.6 F1.5 — GET /api/profiles : liste des 5 profils utilisateur. */
export async function fetchProfiles(): Promise<UserProfile[]> {
  const res = await fetch(`${API_BASE}/api/profiles`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const body = await res.json() as { profiles: UserProfile[] };
  return body.profiles;
}

/** Sprint 4.6 F6 — GET /api/annuaire/orientations : 12 natures de problème. */
export async function fetchOrientations(): Promise<OrientationSummary[]> {
  const res = await fetch(`${API_BASE}/api/annuaire/orientations`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const body = await res.json() as { orientations: OrientationSummary[] };
  return body.orientations;
}

/** Sprint 4.6 F6 — GET /api/annuaire/orientation/<id> : acteurs résolus. */
export async function fetchOrientationDetail(id: string): Promise<OrientationDetail> {
  const res = await fetch(`${API_BASE}/api/annuaire/orientation/${encodeURIComponent(id)}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<OrientationDetail>;
}

/** Sprint 4.6 F6 — GET /api/annuaire/regions : fédérations par région ELISFA. */
export async function fetchRegions(): Promise<RegionInfo[]> {
  const res = await fetch(`${API_BASE}/api/annuaire/regions`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const body = await res.json() as { regions: RegionInfo[] };
  return body.regions;
}

/** Sprint 4.6 F6 — GET /api/annuaire/acteurs : annuaire complet. */
export async function fetchActeurs(): Promise<Acteur[]> {
  const res = await fetch(`${API_BASE}/api/annuaire/acteurs`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const body = await res.json() as { acteurs: Acteur[] };
  return body.acteurs;
}

/** Sprint 4.6 F5 — GET /api/fiches-metiers : 25 fiches CPNEF + docs annexes. */
export async function fetchFichesMetiers(): Promise<FichesMetiersResponse> {
  const res = await fetch(`${API_BASE}/api/fiches-metiers`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<FichesMetiersResponse>;
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
