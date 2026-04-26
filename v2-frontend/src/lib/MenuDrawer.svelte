<script lang="ts">
  // UX-1 Zen-Gemini — Drawer mobile slide-in left (caché sur ≥md)
  import MenuContent from './MenuContent.svelte';

  interface Props {
    open: boolean;
    onClose: () => void;
    onShowProfile: () => void;
    onShowAnnuaire: () => void;
    onShowFiches: () => void;
    onShowLegal: () => void;
  }
  let { open, onClose, onShowProfile, onShowAnnuaire, onShowFiches, onShowLegal }: Props = $props();

  function onKeyDown(e: KeyboardEvent) {
    if (e.key === 'Escape' && open) onClose();
  }
</script>

<svelte:window onkeydown={onKeyDown} />

{#if open}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="fixed inset-0 z-40 md:hidden bg-black/40 animate-fade-in" onclick={onClose}></div>
  <aside
    class="fixed inset-y-0 left-0 z-50 md:hidden w-[82%] max-w-[320px] shadow-2xl animate-slide-in"
    role="dialog"
    aria-modal="true"
    aria-label="Menu principal"
  >
    <MenuContent
      variant="drawer"
      {onShowProfile}
      {onShowAnnuaire}
      {onShowFiches}
      {onShowLegal}
      onNavigate={onClose}
    />
  </aside>
{/if}

<style>
  @keyframes slide-in {
    from { transform: translateX(-100%); }
    to { transform: translateX(0); }
  }
  @keyframes fade-in {
    from { opacity: 0; }
    to { opacity: 1; }
  }
  :global(.animate-slide-in) { animation: slide-in 0.18s ease-out; }
  :global(.animate-fade-in) { animation: fade-in 0.15s ease-out; }
</style>
