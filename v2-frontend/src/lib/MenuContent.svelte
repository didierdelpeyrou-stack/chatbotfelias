<script lang="ts">
  // UX-1 Zen-Gemini — Contenu commun à la Sidebar (desktop) et au MenuDrawer (mobile)
  // Sections : Nouvelle conv · Modules · Profil · Annuaire · Fiches · Légal
  import { onMount } from 'svelte';
  import { MODULES, type Module, type UserProfile } from './types';
  import { chat, setModule, clearConversation } from './store.svelte';
  import { fetchProfiles } from './api';

  interface Props {
    /** Variante : "sidebar" (desktop, fond gris clair) ou "drawer" (mobile, fond blanc). */
    variant: 'sidebar' | 'drawer';
    onShowProfile: () => void;
    onShowAnnuaire: () => void;
    onShowFiches: () => void;
    onShowLegal: () => void;
    /** Appelé après chaque navigation (sert à fermer le drawer en mobile). */
    onNavigate?: () => void;
  }
  let { variant, onShowProfile, onShowAnnuaire, onShowFiches, onShowLegal, onNavigate }: Props = $props();

  let profiles: UserProfile[] = $state([]);
  onMount(async () => {
    try {
      profiles = await fetchProfiles();
    } catch {
      /* silencieux */
    }
  });

  let allowedModules = $derived(() => {
    const p = profiles.find((pp) => pp.id === chat.profileId);
    return p ? p.modules : (MODULES.map((m) => m.id) as Module[]);
  });
  let visibleModules = $derived(MODULES.filter((m) => allowedModules().includes(m.id)));
  let currentProfile = $derived(profiles.find((p) => p.id === chat.profileId) ?? null);

  function pickModule(m: Module) {
    setModule(m);
    onNavigate?.();
  }

  function onNew() {
    if (confirm("Effacer la conversation du module courant ? Cette action est irréversible.")) {
      clearConversation();
      onNavigate?.();
    }
  }

  function call(fn: () => void) {
    fn();
    onNavigate?.();
  }

  // Tints pour modules
  const accentBg: Record<string, string> = {
    blue: 'bg-blue-50 text-blue-700',
    orange: 'bg-orange-50 text-orange-700',
    green: 'bg-green-50 text-green-700',
    navy: 'bg-navy-100 text-navy-900',
  };
</script>

<div class="flex flex-col h-full {variant === 'sidebar' ? 'bg-grey-50 border-r border-grey-200' : 'bg-white'}">
  <!-- Logo / titre -->
  <div class="px-4 py-4 flex items-center gap-2">
    <span class="text-xl">⚖</span>
    <div class="min-w-0">
      <div class="font-semibold text-sm text-navy-900 leading-tight truncate">Chatbot ELISFA</div>
      <div class="text-[11px] text-grey-500 leading-tight">Branche ALISFA</div>
    </div>
  </div>

  <!-- + Nouvelle conversation -->
  <div class="px-3">
    <button
      class="w-full flex items-center gap-2 text-sm font-medium rounded-lg px-3 py-2 border border-grey-300 bg-white hover:border-blue-400 hover:bg-blue-50 hover:text-blue-700 transition cursor-pointer"
      onclick={onNew}
      title="Effacer la conversation du module courant"
    >
      <span class="text-base">＋</span>
      <span>Nouvelle conversation</span>
    </button>
  </div>

  <!-- Modules -->
  <div class="px-3 mt-5">
    <h3 class="text-[10px] uppercase tracking-wider font-bold text-grey-500 px-2 mb-1.5">
      Modules
    </h3>
    <nav class="flex flex-col gap-0.5">
      {#each visibleModules as mod}
        {@const active = chat.module === mod.id}
        <button
          class="flex items-center gap-2.5 text-sm rounded-lg px-2.5 py-2 cursor-pointer transition text-left {active ? `${accentBg[mod.accent]} font-semibold` : 'text-grey-700 hover:bg-grey-100'}"
          onclick={() => pickModule(mod.id)}
        >
          <span class="text-base">{mod.emoji}</span>
          <span class="flex-1 truncate">{mod.label}</span>
          {#if active}
            <span class="text-[10px] uppercase font-bold tracking-wider opacity-70">●</span>
          {/if}
        </button>
      {/each}
    </nav>
  </div>

  <!-- Spacer -->
  <div class="flex-1"></div>

  <!-- Section ressources -->
  <div class="px-3 pt-3 border-t border-grey-200">
    <h3 class="text-[10px] uppercase tracking-wider font-bold text-grey-500 px-2 mb-1.5">
      Ressources
    </h3>
    <nav class="flex flex-col gap-0.5">
      <button
        class="flex items-center gap-2.5 text-sm rounded-lg px-2.5 py-2 text-grey-700 hover:bg-grey-100 cursor-pointer transition text-left"
        onclick={() => call(onShowAnnuaire)}
      >
        <span>🏛</span>
        <span class="flex-1 truncate">Annuaire d'orientation</span>
      </button>
      <button
        class="flex items-center gap-2.5 text-sm rounded-lg px-2.5 py-2 text-grey-700 hover:bg-grey-100 cursor-pointer transition text-left"
        onclick={() => call(onShowFiches)}
      >
        <span>📄</span>
        <span class="flex-1 truncate">Fiches métiers CPNEF</span>
      </button>
      <button
        class="flex items-center gap-2.5 text-sm rounded-lg px-2.5 py-2 text-grey-700 hover:bg-grey-100 cursor-pointer transition text-left"
        onclick={() => call(onShowLegal)}
      >
        <span>ℹ︎</span>
        <span class="flex-1 truncate">Mentions légales</span>
      </button>
    </nav>
  </div>

  <!-- Profil (footer) -->
  <div class="px-3 py-3 border-t border-grey-200">
    <button
      class="w-full flex items-center gap-2.5 text-sm rounded-lg px-2.5 py-2 hover:bg-grey-100 cursor-pointer transition text-left"
      onclick={() => call(onShowProfile)}
      title={currentProfile ? 'Modifier votre profil' : 'Choisir un profil utilisateur'}
    >
      {#if currentProfile}
        <span class="text-base">{currentProfile.icon}</span>
        <div class="flex-1 min-w-0">
          <div class="text-sm font-semibold text-navy-900 truncate">{currentProfile.name}</div>
          <div class="text-[11px] text-grey-500">Modifier le profil</div>
        </div>
      {:else}
        <span class="text-base">👤</span>
        <div class="flex-1 min-w-0">
          <div class="text-sm font-medium text-grey-700">Choisir un profil</div>
          <div class="text-[11px] text-grey-500">Bénévole, pro, président…</div>
        </div>
      {/if}
    </button>
  </div>
</div>
