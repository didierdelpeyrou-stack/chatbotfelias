<script lang="ts">
  import Header from './lib/Header.svelte';
  import ModuleSelector from './lib/ModuleSelector.svelte';
  import ModeSelector from './lib/ModeSelector.svelte';
  import ChatWindow from './lib/ChatWindow.svelte';
  import LegalModal from './lib/LegalModal.svelte';
  import WizardModal from './lib/WizardModal.svelte';
  import WelcomeModal from './lib/WelcomeModal.svelte';
  import AnnuaireModal from './lib/AnnuaireModal.svelte';
  import { chat, submitFromExternal } from './lib/store.svelte';

  let legalOpen = $state(false);
  let wizardOpen = $state(false);
  let annuaireOpen = $state(false);

  // Sprint 4.6 F1.5 — Onboarding : ouvert auto si pas de profil ; ré-ouvrable
  // depuis le chip Header. La distinction se fait via `welcomeIsOnboarding`.
  // chat.profileId === null → 1re visite OU utilisateur a explicitement passé
  // l'onboarding ; on ne ré-ouvre pas tant qu'il n'a pas cliqué sur le chip.
  // Pour différencier, on stocke un flag de "welcome déjà montré" en sessionStorage.
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

<Header
  onShowLegal={() => (legalOpen = true)}
  {onShowProfile}
  onShowAnnuaire={() => (annuaireOpen = true)}
/>
<ModuleSelector />
<ModeSelector onOpenWizard={() => (wizardOpen = true)} />
<ChatWindow />

<LegalModal open={legalOpen} onClose={() => (legalOpen = false)} />
<AnnuaireModal open={annuaireOpen} onClose={() => (annuaireOpen = false)} />
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
