<script lang="ts">
  // Sprint 4.6 F1.5 — Onboarding : sélecteur de profil utilisateur
  // Affiché automatiquement à la 1re visite (chat.profileId === null).
  // Ré-ouvrable via le chip "profil" du Header.
  import { onMount } from 'svelte';
  import type { UserProfile } from './types';
  import { fetchProfiles } from './api';
  import { setProfile } from './store.svelte';

  interface Props {
    open: boolean;
    /** Si true, c'est l'onboarding 1re visite (pas de bouton "ignorer"). */
    isOnboarding?: boolean;
    onClose: () => void;
  }
  let { open, isOnboarding = false, onClose }: Props = $props();

  let profiles: UserProfile[] = $state([]);
  let loading = $state(true);

  onMount(async () => {
    try {
      profiles = await fetchProfiles();
    } catch (e) {
      console.error('fetchProfiles failed', e);
    } finally {
      loading = false;
    }
  });

  function pick(p: UserProfile) {
    setProfile(p.id);
    onClose();
  }

  function skip() {
    // L'utilisateur peut ignorer l'onboarding (chat libre sans profil).
    setProfile(null);
    onClose();
  }

  function onKeyDown(e: KeyboardEvent) {
    if (e.key === 'Escape' && !isOnboarding) onClose();
  }

  let benevoles = $derived(profiles.filter((p) => p.type === 'benevole'));
  let pros = $derived(profiles.filter((p) => p.type === 'professionnel'));
</script>

<svelte:window onkeydown={onKeyDown} />

{#if open}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4"
    onclick={isOnboarding ? undefined : onClose}
  >
    <div
      class="bg-white max-w-3xl w-full max-h-[92vh] overflow-y-auto rounded-xl shadow-xl"
      role="dialog"
      aria-modal="true"
      aria-labelledby="welcome-title"
      tabindex="-1"
      onclick={(e) => e.stopPropagation()}
    >
      <div class="bg-gradient-to-r from-navy-900 to-navy-700 text-white px-5 py-4 rounded-t-xl">
        <h2 id="welcome-title" class="font-semibold text-lg flex items-center gap-2">
          <span>👋</span>
          <span>{isOnboarding ? 'Bienvenue sur Chatbot ELISFA' : 'Modifier votre profil'}</span>
        </h2>
        <p class="text-xs sm:text-sm text-white/80 mt-1">
          Pour adapter les réponses à votre rôle, indiquez-nous qui vous êtes :
        </p>
      </div>

      <div class="px-5 py-4">
        {#if loading}
          <p class="text-sm text-grey-500 py-8 text-center">Chargement…</p>
        {:else}
          <!-- Bénévoles -->
          {#if benevoles.length > 0}
            <h3 class="text-xs font-bold uppercase tracking-wider text-grey-500 mb-2">
              Bénévoles
            </h3>
            <div class="grid sm:grid-cols-2 gap-2 mb-4">
              {#each benevoles as p}
                <button
                  type="button"
                  class="text-left bg-white border-2 border-grey-200 hover:border-purple-400 hover:bg-purple-50 rounded-lg p-3 cursor-pointer transition group"
                  onclick={() => pick(p)}
                >
                  <div class="flex items-start gap-2.5">
                    <span class="text-2xl shrink-0">{p.icon}</span>
                    <div class="min-w-0">
                      <div class="font-semibold text-sm text-navy-900 mb-0.5">{p.name}</div>
                      <div class="text-xs text-grey-600 leading-snug">{p.summary}</div>
                    </div>
                  </div>
                  <span class="absolute top-2 right-2 text-[9px] uppercase tracking-wider text-purple-600 bg-purple-50 px-1.5 py-0.5 rounded font-bold opacity-0 group-hover:opacity-100 transition"></span>
                </button>
              {/each}
            </div>
          {/if}

          <!-- Professionnels -->
          {#if pros.length > 0}
            <h3 class="text-xs font-bold uppercase tracking-wider text-grey-500 mb-2 mt-2">
              Professionnels
            </h3>
            <div class="grid sm:grid-cols-2 gap-2 mb-2">
              {#each pros as p}
                <button
                  type="button"
                  class="text-left bg-white border-2 border-grey-200 hover:border-blue-500 hover:bg-blue-50 rounded-lg p-3 cursor-pointer transition"
                  onclick={() => pick(p)}
                >
                  <div class="flex items-start gap-2.5">
                    <span class="text-2xl shrink-0">{p.icon}</span>
                    <div class="min-w-0">
                      <div class="font-semibold text-sm text-navy-900 mb-0.5">{p.name}</div>
                      <div class="text-xs text-grey-600 leading-snug">{p.summary}</div>
                    </div>
                  </div>
                </button>
              {/each}
            </div>
          {/if}

          <div class="text-center mt-4 pt-3 border-t border-grey-100">
            <button
              type="button"
              class="text-xs text-grey-500 hover:text-grey-700 underline-offset-2 hover:underline cursor-pointer"
              onclick={skip}
            >
              {isOnboarding ? 'Continuer sans profil (chat libre)' : 'Effacer mon profil'}
            </button>
          </div>
        {/if}
      </div>
    </div>
  </div>
{/if}
