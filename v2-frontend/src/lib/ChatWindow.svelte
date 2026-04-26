<script lang="ts">
  // UX-1 Zen-Gemini — Chat centered (max-w-3xl ≈ 720px) + hero welcome screen
  import { chat, addMessage, updateMessage, newId, dispatcher, clearPending, currentMessages } from './store.svelte';
  import { askStream, askOnce } from './api';
  import { MODULES } from './types';
  import { SUGGESTIONS } from './suggestions';
  import MessageBubble from './MessageBubble.svelte';
  import InputBar from './InputBar.svelte';

  interface Props {
    onOpenWizard: () => void;
    onOpenMenu: () => void;
  }
  let { onOpenWizard, onOpenMenu }: Props = $props();

  let busy = $state(false);
  let scrollContainer: HTMLDivElement | undefined = $state();
  let lastQuestion = $state('');

  let messages = $derived(currentMessages());

  $effect(() => {
    messages;
    queueMicrotask(() => {
      if (scrollContainer) scrollContainer.scrollTop = scrollContainer.scrollHeight;
    });
  });

  $effect(() => {
    const req = dispatcher.pending;
    if (req && !busy) {
      const { question, modeOverride } = req;
      clearPending();
      void handleSend(question, modeOverride);
    }
  });

  async function handleSend(text: string, modeOverride?: string | null) {
    if (busy) return;
    busy = true;
    lastQuestion = text;

    addMessage({ id: newId(), role: 'user', content: text });

    const assistantId = newId();
    const startedAt = performance.now();
    const activeMode = modeOverride !== undefined ? modeOverride : (chat.modeByModule[chat.module] ?? null);
    const activeProfile = chat.profileId;
    const activeProfileExtras = chat.profileExtras;
    addMessage({
      id: assistantId,
      role: 'assistant',
      content: '',
      module: chat.module,
      mode: activeMode,
      pending: true,
    });

    try {
      let answerSoFar = '';
      let receivedAnyEvent = false;

      try {
        await askStream({ question: text, module: chat.module, mode: activeMode, profile: activeProfile, profile_extras: activeProfileExtras }, (event) => {
          receivedAnyEvent = true;
          if (event.type === 'sources') {
            updateMessage(assistantId, { sources: event.sources, hors_corpus: event.hors_corpus });
          } else if (event.type === 'delta') {
            answerSoFar += event.text;
            updateMessage(assistantId, { content: answerSoFar });
          } else if (event.type === 'done') {
            updateMessage(assistantId, { pending: false, duration_ms: performance.now() - startedAt });
          } else if (event.type === 'error') {
            throw new Error(event.message);
          }
        });

        const last = currentMessages().find((m) => m.id === assistantId);
        if (last?.pending) {
          updateMessage(assistantId, { pending: false, duration_ms: performance.now() - startedAt });
        }
      } catch (streamErr) {
        if (!receivedAnyEvent || !answerSoFar) {
          const res = await askOnce({ question: text, module: chat.module, mode: activeMode, profile: activeProfile, profile_extras: activeProfileExtras });
          updateMessage(assistantId, {
            content: res.answer,
            sources: res.sources,
            hors_corpus: res.hors_corpus,
            pending: false,
            duration_ms: res.duration_ms ?? performance.now() - startedAt,
          });
        } else {
          throw streamErr;
        }
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erreur inconnue';
      updateMessage(assistantId, { pending: false, error: message });
    } finally {
      busy = false;
    }
  }

  function questionFor(assistantIdx: number): string {
    for (let i = assistantIdx - 1; i >= 0; i--) {
      if (messages[i].role === 'user') return messages[i].content;
    }
    return '';
  }

  let currentModuleMeta = $derived(MODULES.find((m) => m.id === chat.module)!);

  let suggestionHoverClass = $derived(
    currentModuleMeta.accent === 'blue'
      ? 'hover:bg-blue-50 hover:border-blue-300'
      : currentModuleMeta.accent === 'orange'
        ? 'hover:bg-orange-50 hover:border-orange-300'
        : currentModuleMeta.accent === 'green'
          ? 'hover:bg-green-50 hover:border-green-300'
          : 'hover:bg-navy-100 hover:border-navy-700',
  );
</script>

<main class="flex-1 flex flex-col min-h-0 bg-white">
  <!-- Mobile-only floating top bar with hamburger + module label -->
  <div class="md:hidden flex items-center gap-2 px-3 py-2 border-b border-grey-100 bg-white/95 backdrop-blur sticky top-0 z-20">
    <button
      class="w-9 h-9 flex items-center justify-center rounded-lg hover:bg-grey-100 cursor-pointer transition"
      onclick={onOpenMenu}
      aria-label="Ouvrir le menu"
    >
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <path d="M3 6h14M3 10h14M3 14h14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      </svg>
    </button>
    <div class="flex items-center gap-1.5 text-sm font-semibold text-navy-900 truncate">
      <span>{currentModuleMeta.emoji}</span>
      <span class="truncate">{currentModuleMeta.label}</span>
    </div>
  </div>

  <!-- Scrollable conversation area -->
  <div bind:this={scrollContainer} class="flex-1 overflow-y-auto">
    {#if messages.length === 0}
      <!-- Hero welcome screen -->
      <div class="max-w-3xl mx-auto px-4 sm:px-6 py-10 sm:py-16">
        <div class="text-center mb-8">
          <div class="text-6xl sm:text-7xl mb-5">{currentModuleMeta.emoji}</div>
          <h2 class="text-2xl sm:text-3xl font-semibold text-navy-900 mb-2">
            Bonjour 👋
          </h2>
          <p class="text-sm sm:text-base text-grey-600 max-w-xl mx-auto leading-relaxed">
            Module <strong class="text-navy-900">{currentModuleMeta.label}</strong>.
            <span class="hidden sm:inline">{currentModuleMeta.banner}</span>
          </p>
        </div>
        <div class="grid sm:grid-cols-2 gap-2 sm:gap-3 max-w-2xl mx-auto">
          {#each SUGGESTIONS[chat.module] as suggestion}
            <button
              class="bg-white {suggestionHoverClass} border border-grey-200 rounded-xl p-3 sm:p-3.5 text-sm text-grey-700 transition cursor-pointer leading-snug text-left hover:shadow-sm"
              onclick={() => handleSend(suggestion)}
            >
              {suggestion}
            </button>
          {/each}
        </div>
      </div>
    {:else}
      <div class="max-w-3xl mx-auto px-3 sm:px-6 py-4 sm:py-6">
        {#each messages as message, i (message.id)}
          <MessageBubble
            {message}
            questionForFeedback={message.role === 'assistant' ? questionFor(i) : undefined}
          />
        {/each}
      </div>
    {/if}
  </div>

  <InputBar disabled={busy} onSend={handleSend} {onOpenWizard} />
</main>
