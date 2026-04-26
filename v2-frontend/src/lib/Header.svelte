<script lang="ts">
  import { clearConversation, chat } from './store.svelte';
  import { onMount } from 'svelte';
  import { fetchProfiles } from './api';
  import type { UserProfile } from './types';

  interface Props {
    onShowLegal: () => void;
    onShowProfile: () => void;
    onShowAnnuaire: () => void;
  }
  let { onShowLegal, onShowProfile, onShowAnnuaire }: Props = $props();

  let profiles: UserProfile[] = $state([]);
  onMount(async () => {
    try {
      profiles = await fetchProfiles();
    } catch {
      /* silencieux : le chip profil n'apparaîtra pas */
    }
  });

  let currentProfile = $derived(profiles.find((p) => p.id === chat.profileId) ?? null);

  function onClear() {
    if (confirm("Effacer toute la conversation ? Cette action est irréversible.")) {
      clearConversation();
    }
  }
</script>

<header class="bg-gradient-to-r from-navy-900 to-navy-700 text-white shadow-md">
  <div class="max-w-5xl mx-auto px-3 sm:px-4 py-2.5 sm:py-3 flex items-center gap-2 sm:gap-3">
    <span class="text-xl sm:text-2xl">⚖</span>
    <div class="flex-1 min-w-0">
      <h1 class="font-semibold text-sm sm:text-lg truncate leading-tight">
        Chatbot ELISFA
      </h1>
      <p class="text-[11px] sm:text-xs text-white/70 truncate hidden xs:block sm:block">
        Assistant management associatif — branche ALISFA
      </p>
    </div>
    {#if currentProfile}
      <button
        class="text-[11px] sm:text-xs bg-white/10 hover:bg-white/20 border border-white/20 rounded-full px-2 sm:px-3 py-1 sm:py-1.5 transition cursor-pointer flex items-center gap-1"
        title="Modifier votre profil"
        aria-label="Profil utilisateur"
        onclick={onShowProfile}
      >
        <span>{currentProfile.icon}</span>
        <span class="hidden md:inline truncate max-w-[14ch]">{currentProfile.name}</span>
      </button>
    {/if}
    <button
      class="text-[11px] sm:text-xs bg-white/10 hover:bg-white/20 border border-white/20 rounded-md px-2 sm:px-3 py-1 sm:py-1.5 transition cursor-pointer flex items-center gap-1"
      title="Trouver le bon interlocuteur (annuaire d'orientation)"
      aria-label="Annuaire d'orientation"
      onclick={onShowAnnuaire}
    >
      <span>🏛</span>
      <span class="hidden md:inline">Annuaire</span>
    </button>
    <button
      class="text-[11px] sm:text-xs bg-white/10 hover:bg-white/20 border border-white/20 rounded-md px-2 sm:px-3 py-1 sm:py-1.5 transition cursor-pointer flex items-center gap-1"
      title="Mentions légales / RGPD"
      aria-label="Mentions légales"
      onclick={onShowLegal}
    >
      <span class="hidden sm:inline">Mentions légales</span>
      <span class="sm:hidden">ℹ︎</span>
    </button>
    <button
      class="text-[11px] sm:text-xs bg-white/10 hover:bg-white/20 border border-white/20 rounded-md px-2 sm:px-3 py-1 sm:py-1.5 transition cursor-pointer"
      title="Effacer la conversation"
      onclick={onClear}
    >
      <span class="hidden sm:inline">↻ Nouvelle conversation</span>
      <span class="sm:hidden">↻</span>
    </button>
  </div>
</header>
