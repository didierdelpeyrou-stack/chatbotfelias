// Store global de la conversation — Svelte 5 runes
import type { ChatMessage, Module, ProfileExtras } from './types';

function ulid(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 10);
}

const STORAGE_KEY = 'elisfa-v2-state';

interface PersistedState {
  module: Module;
  /**
   * Sprint 4.6 F1.7 — messages segmentés par module.
   * Chaque module garde son historique propre ; switcher de module
   * affiche le sien (ou la home / empty state si aucun message).
   * `messages` (legacy) est accepté en lecture pour migration.
   */
  messagesByModule?: Partial<Record<Module, ChatMessage[]>>;
  messages?: ChatMessage[]; // legacy, migré vers messagesByModule à la lecture
  /** Sprint 4.6 F1 — mode actif par module (mémorisé entre sessions). */
  modeByModule?: Partial<Record<Module, string | null>>;
  /** Sprint 4.6 F1.5 — profil utilisateur sélectionné à l'onboarding. */
  profileId?: string | null;
  /** Sprint 4.6 — caractéristiques de la structure (étape 2 de l'onboarding). */
  profileExtras?: ProfileExtras;
}

function defaultState(): Required<Omit<PersistedState, 'messages'>> {
  return {
    module: 'juridique',
    messagesByModule: {},
    modeByModule: {},
    profileId: null,
    profileExtras: {},
  };
}

function loadState(): Required<Omit<PersistedState, 'messages'>> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return defaultState();
    const parsed = JSON.parse(raw) as PersistedState;
    const out = defaultState();
    out.module = parsed.module ?? 'juridique';

    // Migration : si l'utilisateur a un ancien state avec `messages` global,
    // on le migre vers messagesByModule[module].
    const byModule: Partial<Record<Module, ChatMessage[]>> = parsed.messagesByModule ?? {};
    if (parsed.messages && parsed.messages.length > 0 && !parsed.messagesByModule) {
      byModule[out.module] = parsed.messages;
    }
    // Sécurité : invalide messages pendant streaming si rechargement à mi-course
    for (const mod of Object.keys(byModule) as Module[]) {
      byModule[mod] = (byModule[mod] || []).map((m) => ({ ...m, pending: false }));
    }
    out.messagesByModule = byModule;

    out.modeByModule = parsed.modeByModule ?? {};
    out.profileId = parsed.profileId ?? null;
    out.profileExtras = parsed.profileExtras ?? {};
    return out;
  } catch {
    return defaultState();
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
  /** Sprint 4.6 F1.7 — messages segmentés par module. */
  messagesByModule: initial.messagesByModule as Partial<Record<Module, ChatMessage[]>>,
  /** Sprint 4.6 F1 — mode actif par module. null = chat libre. */
  modeByModule: initial.modeByModule as Partial<Record<Module, string | null>>,
  /** Sprint 4.6 F1.5 — profil utilisateur (null = pas encore sélectionné). */
  profileId: initial.profileId as string | null,
  /** Sprint 4.6 — caractéristiques structure (étape 2 onboarding). */
  profileExtras: initial.profileExtras as ProfileExtras,
});

/**
 * Accesseur réactif : messages du module courant. Lecture seule —
 * pour modifier, utiliser addMessage / updateMessage / clearConversation.
 */
export function currentMessages(): ChatMessage[] {
  return chat.messagesByModule[chat.module] ?? [];
}

// Persiste à chaque changement (debounced via microtask)
let pending = false;
$effect.root(() => {
  $effect(() => {
    // touch reactive deps
    const snap: PersistedState = {
      module: chat.module,
      messagesByModule: chat.messagesByModule,
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
  const m = chat.module;
  const list = chat.messagesByModule[m] ?? [];
  chat.messagesByModule = { ...chat.messagesByModule, [m]: [...list, msg] };
}

export function updateMessage(id: string, patch: Partial<ChatMessage>): void {
  const m = chat.module;
  const list = chat.messagesByModule[m] ?? [];
  const idx = list.findIndex((x) => x.id === id);
  if (idx < 0) return;
  const next = [...list];
  next[idx] = { ...next[idx], ...patch };
  chat.messagesByModule = { ...chat.messagesByModule, [m]: next };
}

/** Efface les messages du module courant (la home revient automatiquement). */
export function clearConversation(): void {
  chat.messagesByModule = { ...chat.messagesByModule, [chat.module]: [] };
}

/** Efface l'historique de TOUS les modules. */
export function clearAllConversations(): void {
  chat.messagesByModule = {};
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
