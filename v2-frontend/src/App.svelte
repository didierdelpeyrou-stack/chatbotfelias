<script lang="ts">
  // UX-1 Zen-Gemini — Layout Sidebar (desktop) + Drawer (mobile) + chat plein écran
  import Sidebar from './lib/Sidebar.svelte';
  import MenuDrawer from './lib/MenuDrawer.svelte';
  import ChatWindow from './lib/ChatWindow.svelte';
  import LegalModal from './lib/LegalModal.svelte';
  import WizardModal from './lib/WizardModal.svelte';
  import WelcomeModal from './lib/WelcomeModal.svelte';
  import AnnuaireModal from './lib/AnnuaireModal.svelte';
  import FichesMetiersModal from './lib/FichesMetiersModal.svelte';
  import { chat, submitFromExternal } from './lib/store.svelte';

  let legalOpen = $state(false);
  let wizardOpen = $state(false);
  let annuaireOpen = $state(false);
  let fichesOpen = $state(false);
  let drawerOpen = $state(false);

  const ONBOARDING_SHOWN_KEY = 'elisfa-v2-onboarding-shown';
  let welcomeOpen = $state(false);
  let welcomeIsOnboarding = $state(true);

  $effect(() => {
    if (chat.profileId === null && !sessionStorage.getItem(ONBOARDING_SHOWN_KEY)) {
      welcomeOpen = true;
      welcomeIsOnboarding = true;
      sessionStorage.setItem(ONBOARDING_SHOWN_KEY, '1');
    }
  });

  function onShowProfile() {
    welcomeIsOnboarding = false;
    welcomeOpen = true;
  }

  function onWizardSubmit(synthesis: string, modeId: string) {
    submitFromExternal({ question: synthesis, modeOverride: modeId });
  }
</script>

<div class="flex min-h-screen bg-white">
  <!-- Desktop sidebar (hidden on mobile) -->
  <Sidebar
    {onShowProfile}
    onShowAnnuaire={() => (annuaireOpen = true)}
    onShowFiches={() => (fichesOpen = true)}
    onShowLegal={() => (legalOpen = true)}
  />

  <!-- Mobile drawer (hidden on desktop) -->
  <MenuDrawer
    open={drawerOpen}
    onClose={() => (drawerOpen = false)}
    {onShowProfile}
    onShowAnnuaire={() => (annuaireOpen = true)}
    onShowFiches={() => (fichesOpen = true)}
    onShowLegal={() => (legalOpen = true)}
  />

  <!-- Main chat area (flex-1) -->
  <ChatWindow
    onOpenWizard={() => (wizardOpen = true)}
    onOpenMenu={() => (drawerOpen = true)}
  />
</div>

<LegalModal open={legalOpen} onClose={() => (legalOpen = false)} />
<AnnuaireModal open={annuaireOpen} onClose={() => (annuaireOpen = false)} />
<FichesMetiersModal open={fichesOpen} onClose={() => (fichesOpen = false)} />
<WizardModal
  open={wizardOpen}
  module={chat.module}
  onClose={() => (wizardOpen = false)}
  onSubmit={onWizardSubmit}
/>
<WelcomeModal
  open={welcomeOpen}
  isOnboarding={welcomeIsOnboarding}
  onClose={() => (welcomeOpen = false)}
/>
