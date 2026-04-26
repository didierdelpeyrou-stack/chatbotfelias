<script lang="ts">
  // Sprint 4.6 F4 — Wizard guidé multi-étapes
  // À l'envoi : construit une synthèse + envoie via /api/ask avec mode=wizard_<module>
  import type { Module } from './types';
  import { getWizard, buildWizardSynthesis } from './wizards';

  interface Props {
    open: boolean;
    module: Module;
    onClose: () => void;
    /** Callback invoqué avec (questionSynthesis, modeId) — le ChatWindow envoie. */
    onSubmit: (synthesis: string, modeId: string) => void;
  }

  let { open, module, onClose, onSubmit }: Props = $props();

  let config = $derived(getWizard(module));
  let stepIdx = $state(0);
  let answers = $state<Record<string, string>>({});

  // Reset state à l'ouverture
  $effect(() => {
    if (open) {
      stepIdx = 0;
      answers = {};
    }
  });

  let currentStep = $derived(config.steps[stepIdx]);
  let isLastStep = $derived(stepIdx === config.steps.length - 1);
  let canNext = $derived(() => {
    if (!currentStep) return false;
    if (currentStep.required && !answers[currentStep.id]?.trim()) return false;
    return true;
  });

  function setAnswer(id: string, value: string) {
    answers[id] = value;
  }

  function next() {
    if (!canNext()) return;
    if (isLastStep) {
      submit();
    } else {
      stepIdx++;
    }
  }

  function prev() {
    if (stepIdx > 0) stepIdx--;
  }

  function submit() {
    const synthesis = buildWizardSynthesis(config, answers);
    onSubmit(synthesis, config.modeId);
    onClose();
  }

  function onKeyDown(e: KeyboardEvent) {
    if (e.key === 'Escape') onClose();
  }
</script>

<svelte:window onkeydown={onKeyDown} />

{#if open}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4"
    onclick={onClose}
  >
    <div
      class="bg-white max-w-2xl w-full max-h-[90vh] overflow-hidden rounded-xl shadow-xl flex flex-col"
      role="dialog"
      aria-modal="true"
      aria-labelledby="wizard-title"
      tabindex="-1"
      onclick={(e) => e.stopPropagation()}
    >
      <!-- Header -->
      <div class="bg-gradient-to-r from-navy-900 to-navy-700 text-white px-5 py-3 flex items-center justify-between">
        <div class="min-w-0 flex-1">
          <h2 id="wizard-title" class="font-semibold text-base truncate">{config.title}</h2>
          <p class="text-xs text-white/70 truncate">{config.subtitle}</p>
        </div>
        <button
          class="text-white/80 hover:text-white text-xl leading-none cursor-pointer w-7 h-7 flex items-center justify-center rounded-md hover:bg-white/10"
          onclick={onClose}
          aria-label="Fermer"
        >×</button>
      </div>

      <!-- Progress -->
      <div class="px-5 pt-3 pb-2 border-b border-grey-200">
        <div class="flex items-center justify-between text-xs text-grey-600 mb-1.5">
          <span>Étape {stepIdx + 1} / {config.steps.length}</span>
          <span class="text-grey-400">{Math.round(((stepIdx + 1) / config.steps.length) * 100)}%</span>
        </div>
        <div class="h-1 bg-grey-100 rounded-full overflow-hidden">
          <div
            class="h-full bg-blue-600 transition-all duration-200"
            style="width: {((stepIdx + 1) / config.steps.length) * 100}%"
          ></div>
        </div>
      </div>

      <!-- Step content -->
      <div class="flex-1 overflow-y-auto px-5 py-5">
        {#if currentStep}
          <h3 class="text-base font-semibold text-grey-800 leading-snug mb-2">
            {currentStep.label}
            {#if currentStep.required}
              <span class="text-red-500 text-xs ml-1">*</span>
            {/if}
          </h3>
          {#if currentStep.help}
            <p class="text-xs text-grey-500 mb-3 leading-relaxed">{currentStep.help}</p>
          {/if}

          {#if currentStep.type === 'choice'}
            <div class="flex flex-col gap-2 mt-2">
              {#each currentStep.options as option}
                {@const selected = answers[currentStep.id] === option}
                <button
                  type="button"
                  class="text-left text-sm rounded-lg px-4 py-2.5 transition cursor-pointer border {selected ? 'bg-blue-50 border-blue-500 text-blue-900 ring-2 ring-blue-500/20' : 'bg-white border-grey-200 text-grey-700 hover:border-grey-300 hover:bg-grey-50'}"
                  onclick={() => setAnswer(currentStep.id, option)}
                >
                  {option}
                </button>
              {/each}
            </div>
          {:else if currentStep.type === 'text'}
            <textarea
              class="w-full mt-2 border border-grey-300 rounded-lg p-3 text-sm leading-relaxed focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none resize-none min-h-[120px]"
              placeholder={currentStep.placeholder ?? ''}
              value={answers[currentStep.id] ?? ''}
              oninput={(e) => setAnswer(currentStep.id, (e.target as HTMLTextAreaElement).value)}
            ></textarea>
          {/if}
        {/if}
      </div>

      <!-- Footer -->
      <div class="border-t border-grey-200 px-5 py-3 flex items-center justify-between bg-grey-50">
        <button
          class="text-sm text-grey-600 hover:text-grey-900 cursor-pointer disabled:text-grey-300 disabled:cursor-not-allowed"
          disabled={stepIdx === 0}
          onclick={prev}
        >
          ← Précédent
        </button>
        <div class="text-xs text-grey-400 hidden sm:block">
          Diagnostic guidé — synthèse envoyée pour analyse
        </div>
        <button
          class="bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg px-4 py-2 cursor-pointer transition disabled:bg-grey-300 disabled:cursor-not-allowed"
          disabled={!canNext()}
          onclick={next}
        >
          {isLastStep ? 'Lancer le diagnostic →' : 'Suivant →'}
        </button>
      </div>
    </div>
  </div>
{/if}
