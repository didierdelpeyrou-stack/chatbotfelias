<script lang="ts">
  // UX-1 Zen-Gemini — Sidebar desktop (≥md), 260px fixe à gauche
  import MenuContent from './MenuContent.svelte';

  interface Props {
    onShowProfile: () => void;
    onShowAnnuaire: () => void;
    onShowFiches: () => void;
    onShowLegal: () => void;
  }
  let { onShowProfile, onShowAnnuaire, onShowFiches, onShowLegal }: Props = $props();
</script>

<aside class="hidden md:flex md:w-[260px] md:shrink-0 h-screen sticky top-0">
  <MenuContent
    variant="sidebar"
    {onShowProfile}
    {onShowAnnuaire}
    {onShowFiches}
    {onShowLegal}
  />
</aside>
