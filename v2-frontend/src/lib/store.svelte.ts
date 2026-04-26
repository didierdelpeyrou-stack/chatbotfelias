// Store global de la conversation — Svelte 5 runes
import type { ChatMessage, Module, ProfileExtras } from './types';

function ulid(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 10);
}

const STORAGE_KEY = 'elisfa-v2-state';

interface PersistedState {
  module: Module;
  messages: ChatMessage[];
  /** Sprint 4.6 F1 — mode actif par module (mémorisé entre sessions). */
  modeByModule?: Partial<Record<Module, string | null>>;
  /** Sprint 4.6 F1.5 — profil utilisateur sélectionné à l'onboarding. */
  profileId?: string | null;
  /** Sprint 4.6 — caractéristiques de la structure (étape 2 de l'onboarding). */
  profileExtras?: ProfileExtras;
}

function loadState(): PersistedState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { module: 'juridique', messages: [], modeByModule: {}, profileId: null, profileExtras: {} };
    const parsed = JSON.parse(raw) as PersistedState;
    // Sécurité : invalide messages pendant streaming si rechargement à mi-course
    parsed.messages = (parsed.messages || []).map((m) => ({ ...m, pending: false }));
    parsed.modeByModule = parsed.modeByModule ?? {};
    parsed.profileId = parsed.profileId ?? null;
    parsed.profileExtras = parsed.profileExtras ?? {};
    return parsed;
  } catch {
    return { module: 'juridique', messages: [], modeByModule: {}, profileId: null, profileExtras: {} };
  }
}

function saveState(s: PersistedState): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
  } catch {
    /* quota exceeded ou mode privé : on ignore */
  }
}

const initial = loadState();

export const chat = $state({
  module: initial.module as Module,
  messages: initial.messages,
  /** Sprint 4.6 F1 — mode actif par module. null = chat libre. */
  modeByModule: initial.modeByModule ?? {} as Partial<Record<Module, string | null>>,
  /** Sprint 4.6 F1.5 — profil utilisateur (null = pas encore sélectionné). */
  profileId: initial.profileId as string | null,
  /** Sprint 4.6 — caractéristiques structure (étape 2 onboarding). */
  profileExtras: (initial.profileExtras ?? {}) as ProfileExtras,
});

// Persiste à chaque changement (debounced via microtask)
let pending = false;
$effect.root(() => {
  $effect(() => {
    // touch reactive deps
    const snap = {
      module: chat.module,
      messages: chat.messages,
      modeByModule: chat.modeByModule,
      profileId: chat.profileId,
      profileExtras: chat.profileExtras,
    };
    if (pending) return;
    pending = true;
    queueMicrotask(() => {
      saveState(snap);
      pending = false;
    });
  });
});

export function newId(): string {
  return ulid();
}

export function addMessage(msg: ChatMessage): void {
  chat.messages.push(msg);
}

export function updateMessage(id: string, patch: Partial<ChatMessage>): void {
  const idx = chat.messages.findIndex((m) => m.id === id);
  if (idx >= 0) chat.messages[idx] = { ...chat.messages[idx], ...patch };
}

export function clearConversation(): void {
  chat.messages = [];
}

export function setModule(m: Module): void {
  chat.module = m;
}

/** Sprint 4.6 F1 — change le mode actif pour le module courant (ou un autre). */
export function setMode(modeId: string | null, module?: Module): void {
  const m = module ?? chat.module;
  chat.modeByModule = { ...chat.modeByModule, [m]: modeId };
}

/** Sprint 4.6 F1 — mode actif pour le module courant (ou null si aucun). */
export function getCurrentMode(): string | null {
  return chat.modeByModule[chat.module] ?? null;
}

/** Sprint 4.6 F1.5 — change le profil utilisateur (persisté localStorage). */
export function setProfile(profileId: string | null): void {
  chat.profileId = profileId;
}

/** Sprint 4.6 — met à jour les caractéristiques structure (merge partiel). */
export function setProfileExtras(extras: Partial<ProfileExtras>): void {
  chat.profileExtras = { ...chat.profileExtras, ...extras };
}

/** Sprint 4.6 — efface les caractéristiques structure. */
export function clearProfileExtras(): void {
  chat.profileExtras = {};
}

/**
 * Sprint 4.6 F4 — file d'attente d'envoi externe (wizard, futurs CTA, …).
 * Format : { question, modeOverride? } ; remis à null après consommation.
 */
export interface PendingSubmission {
  question: string;
  modeOverride?: string | null;
}

export const dispatcher = $state({
  pending: null as PendingSubmission | null,
});

export function submitFromExternal(req: PendingSubmission): void {
  dispatcher.pending = req;
}

export function clearPending(): void {
  dispatcher.pending = null;
}
