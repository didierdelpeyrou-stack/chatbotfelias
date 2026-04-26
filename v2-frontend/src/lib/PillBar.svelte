<script lang="ts">
  // UX-1 Zen-Gemini — Pills module + mode + diagnostic juste au-dessus de l'input
  // Pattern Gemini / ChatGPT 5 : sélecteurs contextuels près de la saisie
  import { onMount } from 'svelte';
  import { MODULES, type Mode, type Module, type UserProfile } from './types';
  import { chat, setMode, setModule } from './store.svelte';
  import { fetchModes, fetchProfiles } from './api';

  interface Props {
    onOpenWizard: () => void;
  }
  let { onOpenWizard }: Props = $props();

  let allModes: Mode[] = $state([]);
  let profiles: UserProfile[] = $state([]);

  onMount(async () => {
    try {
      [allModes, profiles] = await Promise.all([fetchModes(), fetchProfiles()]);
    } catch {
      /* silencieux */
    }
  });

  // Module pill state
  let modulePopover = $state(false);
  let modePopover = $state(false);

  let allowedModules = $derived(() => {
    const p = profiles.find((pp) => pp.id === chat.profileId);
    return p ? p.modules : (MODULES.map((m) => m.id) as Module[]);
  });
  let visibleModules = $derived(MODULES.filter((m) => allowedModules().includes(m.id)));

  let currentModuleMeta = $derived(MODULES.find((m) => m.id === chat.module)!);

  // Modes filtered by current module, excluding wizards (those = bouton dédié)
  let regularModes = $derived(
    allModes.filter((m) => m.module === chat.module && !m.id.startsWith('wizard_')),
  );
  let hasWizard = $derived(allModes.some((m) => m.module === chat.module && m.id.startsWith('wizard_')));
  let activeModeId = $derived(chat.modeByModule[chat.module] ?? null);
  let activeMode = $derived(regularModes.find((m) => m.id === activeModeId) ?? null);

  function selectModule(m: Module) {
    setModule(m);
    modulePopover = false;
  }

  function selectMode(modeId: string | null) {
    setMode(modeId);
    modePopover = false;
  }

  function onDocClick(e: MouseEvent) {
    const t = e.target as HTMLElement;
    if (!t.closest('[data-pill]')) {
      modulePopover = false;
      modePopover = false;
    }
  }

  function onKeyDown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      modulePopover = false;
      modePopover = false;
    }
  }
</script>

<svelte:document onclick={onDocClick} />
<svelte:window onkeydown={onKeyDown} />

<div class="flex items-center gap-2 flex-wrap">
  <!-- Module pill -->
  <div class="relative" data-pill>
    <button
      class="flex items-center gap-1.5 text-xs sm:text-sm font-medium rounded-full px-3 py-1.5 border border-grey-300 bg-white hover:border-grey-400 hover:bg-grey-50 cursor-pointer transition"
      onclick={() => { modulePopover = !modulePopover; modePopover = false; }}
      aria-haspopup="menu"
      aria-expanded={modulePopover}
    >
      <span>{currentModuleMeta.emoji}</span>
      <span>{currentModuleMeta.short}</span>
      <span class="text-grey-400 text-[10px]">▾</span>
    </button>
    {#if modulePopover}
      <div
        class="absolute bottom-full mb-1 left-0 z-30 min-w-[200px] bg-white border border-grey-200 rounded-lg shadow-lg py-1 animate-pop"
        role="menu"
      >
        {#each visibleModules as mod}
          {@const active = chat.module === mod.id}
          <button
            class="w-full flex items-center gap-2 text-sm px-3 py-2 cursor-pointer text-left transition {active ? 'bg-grey-50 font-semibold text-navy-900' : 'text-grey-700 hover:bg-grey-50'}"
            onclick={() => selectModule(mod.id)}
            role="menuitem"
          >
            <span class="text-base">{mod.emoji}</span>
            <span class="flex-1 truncate">{mod.label}</span>
            {#if active}<span class="text-blue-600">✓</span>{/if}
          </button>
        {/each}
      </div>
    {/if}
  </div>

  <!-- Mode pill -->
  {#if regularModes.length > 0}
    <div class="relative" data-pill>
      <button
        class="flex items-center gap-1.5 text-xs sm:text-sm rounded-full px-3 py-1.5 border border-grey-300 bg-white hover:border-grey-400 hover:bg-grey-50 cursor-pointer transition"
        onclick={() => { modePopover = !modePopover; modulePopover = false; }}
        aria-haspopup="menu"
        aria-expanded={modePopover}
      >
        {#if activeMode}
          <span>{activeMode.icon}</span>
          <span class="font-medium">{activeMode.label}</span>
        {:else}
          <span class="text-grey-700">Chat libre</span>
        {/if}
        <span class="text-grey-400 text-[10px]">▾</span>
      </button>
      {#if modePopover}
        <div
          class="absolute bottom-full mb-1 left-0 z-30 min-w-[220px] bg-white border border-grey-200 rounded-lg shadow-lg py-1 animate-pop"
          role="menu"
        >
          <button
            class="w-full flex items-center gap-2 text-sm px-3 py-2 cursor-pointer text-left transition {activeModeId === null ? 'bg-grey-50 font-semibold text-navy-900' : 'text-grey-700 hover:bg-grey-50'}"
            onclick={() => selectMode(null)}
            role="menuitem"
          >
            <span class="text-base">💬</span>
            <span class="flex-1">Chat libre</span>
            {#if activeModeId === null}<span class="text-blue-600">✓</span>{/if}
          </button>
          {#each regularModes as mode}
            {@const active = activeModeId === mode.id}
            <button
              class="w-full flex items-start gap-2 text-sm px-3 py-2 cursor-pointer text-left transition {active ? 'bg-grey-50 font-semibold text-navy-900' : 'text-grey-700 hover:bg-grey-50'}"
              onclick={() => selectMode(mode.id)}
              role="menuitem"
            >
              <span class="text-base shrink-0">{mode.icon}</span>
              <div class="min-w-0 flex-1">
                <div class="truncate">{mode.label}</div>
              </div>
              {#if active}<span class="text-blue-600">✓</span>{/if}
            </button>
          {/each}
        </div>
      {/if}
    </div>
  {/if}

  <!-- Diagnostic guidé (wizard) -->
  {#if hasWizard}
    <button
      class="flex items-center gap-1.5 text-xs sm:text-sm font-medium rounded-full px-3 py-1.5 border border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100 hover:border-blue-300 cursor-pointer transition"
      onclick={onOpenWizard}
      title="Diagnostic guidé multi-étapes"
    >
      <span>🧭</span>
      <span class="hidden sm:inline">Diagnostic guidé</span>
      <span class="sm:hidden">Diag.</span>
    </button>
  {/if}
</div>

<style>
  @keyframes pop {
    from { opacity: 0; transform: translateY(4px) scale(0.98); }
    to { opacity: 1; transform: translateY(0) scale(1); }
  }
  :global(.animate-pop) { animation: pop 0.12s ease-out; transform-origin: bottom left; }
</style>
