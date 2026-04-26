<script lang="ts">
  import Header from './lib/Header.svelte';
  import ModuleSelector from './lib/ModuleSelector.svelte';
  import ModeSelector from './lib/ModeSelector.svelte';
  import ChatWindow from './lib/ChatWindow.svelte';
  import LegalModal from './lib/LegalModal.svelte';

  let legalOpen = $state(false);
</script>

<Header onShowLegal={() => (legalOpen = true)} />
<ModuleSelector />
<ModeSelector />
<ChatWindow />
<LegalModal open={legalOpen} onClose={() => (legalOpen = false)} />
