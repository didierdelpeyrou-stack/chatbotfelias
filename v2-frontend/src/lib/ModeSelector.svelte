<script lang="ts">
  // Sprint 4.6 F1 — sélecteur de mode d'usage par module
  // (urgence, analyse, rédaction, calcul, dispositifs, bénévolat, …)
  import { onMount } from 'svelte';
  import type { Mode } from './types';
  import { fetchModes } from './api';
  import { chat, setMode } from './store.svelte';

  let allModes: Mode[] = $state([]);
  let loading = $state(true);
  let error = $state<string | null>(null);

  onMount(async () => {
    try {
      allModes = await fetchModes();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Erreur chargement modes';
    } finally {
      loading = false;
    }
  });

  let modulesModes = $derived(allModes.filter((m) => m.module === chat.module));
  let activeModeId = $derived(chat.modeByModule[chat.module] ?? null);

  function pick(modeId: string | null) {
    setMode(modeId);
  }
</script>

{#if loading || error}
  <!-- Bandeau silencieux pendant chargement / si erreur (les modes sont optionnels) -->
{:else if modulesModes.length > 0}
  <div class="border-b border-grey-200 bg-grey-50">
    <div class="max-w-5xl mx-auto px-3 sm:px-4 py-2 flex gap-1 overflow-x-auto items-center">
      <span class="text-[11px] sm:text-xs text-grey-500 font-medium mr-1 shrink-0">
        Mode :
      </span>
      <button
        class="text-[11px] sm:text-xs rounded-md px-2 py-1 whitespace-nowrap cursor-pointer transition border {activeModeId === null ? 'bg-white text-grey-800 border-grey-300 shadow-sm' : 'border-transparent text-grey-500 hover:bg-white hover:text-grey-700'}"
        onclick={() => pick(null)}
      >
        Chat libre
      </button>
      {#each modulesModes as mode}
        {@const active = activeModeId === mode.id}
        <button
          class="flex items-center gap-1 text-[11px] sm:text-xs rounded-md px-2 py-1 whitespace-nowrap cursor-pointer transition border {active ? 'bg-white text-grey-800 border-grey-300 shadow-sm' : 'border-transparent text-grey-500 hover:bg-white hover:text-grey-700'}"
          onclick={() => pick(mode.id)}
          title={mode.placeholder}
        >
          <span>{mode.icon}</span>
          <span>{mode.label}</span>
        </button>
      {/each}
    </div>
  </div>
{/if}
