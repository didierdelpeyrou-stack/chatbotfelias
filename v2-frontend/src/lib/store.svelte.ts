// Store global de la conversation — Svelte 5 runes
import type { ChatMessage, Module } from './types';

function ulid(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 10);
}

const STORAGE_KEY = 'elisfa-v2-state';

interface PersistedState {
  module: Module;
  messages: ChatMessage[];
  /** Sprint 4.6 F1 — mode actif par module (mémorisé entre sessions). */
  modeByModule?: Partial<Record<Module, string | null>>;
}

function loadState(): PersistedState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { module: 'juridique', messages: [], modeByModule: {} };
    const parsed = JSON.parse(raw) as PersistedState;
    // Sécurité : invalide messages pendant streaming si rechargement à mi-course
    parsed.messages = (parsed.messages || []).map((m) => ({ ...m, pending: false }));
    parsed.modeByModule = parsed.modeByModule ?? {};
    return parsed;
  } catch {
    return { module: 'juridique', messages: [], modeByModule: {} };
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
