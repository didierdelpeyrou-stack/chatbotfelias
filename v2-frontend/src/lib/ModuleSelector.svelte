<script lang="ts">
  import { onMount } from 'svelte';
  import { MODULES, type Module, type UserProfile } from './types';
  import { chat, setModule } from './store.svelte';
  import { fetchProfiles } from './api';

  const accentClasses: Record<string, { bg: string; ring: string; text: string }> = {
    blue: { bg: 'bg-blue-50', ring: 'ring-blue-500', text: 'text-blue-700' },
    orange: { bg: 'bg-orange-50', ring: 'ring-orange-500', text: 'text-orange-600' },
    green: { bg: 'bg-green-50', ring: 'ring-green-600', text: 'text-green-700' },
    navy: { bg: 'bg-navy-100', ring: 'ring-navy-700', text: 'text-navy-900' },
  };

  // Sprint 4.6 F1.5 — Filtre les modules selon le profil utilisateur sélectionné
  let profiles: UserProfile[] = $state([]);
  onMount(async () => {
    try {
      profiles = await fetchProfiles();
    } catch {
      /* silencieux : on affichera les 4 modules par défaut */
    }
  });

  let allowedModules = $derived(() => {
    const p = profiles.find((pp) => pp.id === chat.profileId);
    return p ? p.modules : (MODULES.map((m) => m.id) as Module[]);
  });

  let visibleModules = $derived(MODULES.filter((m) => allowedModules().includes(m.id)));

  // Si le module courant n'est pas autorisé par le nouveau profil, on bascule sur le premier autorisé
  $effect(() => {
    if (visibleModules.length > 0 && !visibleModules.find((m) => m.id === chat.module)) {
      setModule(visibleModules[0].id);
    }
  });

  function pick(m: Module) {
    setModule(m);
  }
</script>

<div class="border-b border-grey-200 bg-white">
  <div class="max-w-5xl mx-auto px-4 py-2 flex gap-1.5 overflow-x-auto">
    {#each visibleModules as mod}
      {@const a = accentClasses[mod.accent]}
      {@const active = chat.module === mod.id}
      <button
        class="flex items-center gap-1.5 rounded-lg px-2.5 sm:px-3 py-1.5 text-xs sm:text-sm font-medium whitespace-nowrap cursor-pointer transition border {active ? `${a.bg} ${a.text} border-transparent ring-2 ${a.ring}` : 'border-grey-200 text-grey-600 hover:bg-grey-50'}"
        onclick={() => pick(mod.id)}
        aria-label={mod.label}
      >
        <span>{mod.emoji}</span>
        <span class="hidden sm:inline">{mod.label}</span>
        <span class="sm:hidden">{mod.short}</span>
      </button>
    {/each}
  </div>
  {#each MODULES as mod}
    {#if chat.module === mod.id}
      <div class="max-w-5xl mx-auto px-4 pb-3 pt-1 text-xs text-grey-600 leading-relaxed">
        {mod.banner}
      </div>
    {/if}
  {/each}
</div>
