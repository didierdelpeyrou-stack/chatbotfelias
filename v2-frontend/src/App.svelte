<script lang="ts">
  import Header from './lib/Header.svelte';
  import ModuleSelector from './lib/ModuleSelector.svelte';
  import ModeSelector from './lib/ModeSelector.svelte';
  import ChatWindow from './lib/ChatWindow.svelte';
  import LegalModal from './lib/LegalModal.svelte';
  import WizardModal from './lib/WizardModal.svelte';
  import { chat, submitFromExternal } from './lib/store.svelte';

  let legalOpen = $state(false);
  let wizardOpen = $state(false);

  function onWizardSubmit(synthesis: string, modeId: string) {
    // Push une soumission externe — ChatWindow la consomme via $effect.
    submitFromExternal({ question: synthesis, modeOverride: modeId });
  }
</script>

<Header onShowLegal={() => (legalOpen = true)} />
<ModuleSelector />
<ModeSelector onOpenWizard={() => (wizardOpen = true)} />
<ChatWindow />

<LegalModal open={legalOpen} onClose={() => (legalOpen = false)} />
<WizardModal
  open={wizardOpen}
  module={chat.module}
  onClose={() => (wizardOpen = false)}
  onSubmit={onWizardSubmit}
/>
