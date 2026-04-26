<script lang="ts">
  import { chat, addMessage, updateMessage, newId, dispatcher, clearPending } from './store.svelte';
  import { askStream, askOnce } from './api';
  import { MODULES } from './types';
  import { SUGGESTIONS } from './suggestions';
  import MessageBubble from './MessageBubble.svelte';
  import InputBar from './InputBar.svelte';

  let busy = $state(false);
  let scrollContainer: HTMLDivElement | undefined = $state();
  let lastQuestion = $state('');

  // Auto-scroll en bas à chaque nouveau message ou token
  $effect(() => {
    chat.messages; // dépendance
    queueMicrotask(() => {
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight;
      }
    });
  });

  // Sprint 4.6 F4 — consomme les soumissions externes (wizard, CTA, …)
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

    // 1. Push message utilisateur
    addMessage({
      id: newId(),
      role: 'user',
      content: text,
    });

    // 2. Push placeholder assistant en streaming
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
      // Phase 2 : streaming SSE — sources reçues d'abord, puis tokens progressifs.
      let answerSoFar = '';
      let receivedAnyEvent = false;

      try {
        await askStream({ question: text, module: chat.module, mode: activeMode, profile: activeProfile, profile_extras: activeProfileExtras }, (event) => {
          receivedAnyEvent = true;
          if (event.type === 'sources') {
            updateMessage(assistantId, {
              sources: event.sources,
              hors_corpus: event.hors_corpus,
            });
          } else if (event.type === 'delta') {
            answerSoFar += event.text;
            updateMessage(assistantId, { content: answerSoFar });
          } else if (event.type === 'done') {
            updateMessage(assistantId, {
              pending: false,
              duration_ms: performance.now() - startedAt,
            });
          } else if (event.type === 'error') {
            throw new Error(event.message);
          }
        });

        // Sécurité : le serveur n'a pas envoyé 'done' explicitement
        const last = chat.messages.find((m) => m.id === assistantId);
        if (last?.pending) {
          updateMessage(assistantId, {
            pending: false,
            duration_ms: performance.now() - startedAt,
          });
        }
      } catch (streamErr) {
        // Stream KO avant tout token : fallback /api/ask non-streaming
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
      updateMessage(assistantId, {
        pending: false,
        error: message,
      });
    } finally {
      busy = false;
    }
  }

  // Question liée à chaque réponse assistant pour le feedback (parcours pairé)
  function questionFor(assistantIdx: number): string {
    for (let i = assistantIdx - 1; i >= 0; i--) {
      if (chat.messages[i].role === 'user') return chat.messages[i].content;
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

<div class="flex-1 flex flex-col min-h-0 bg-grey-50">
  <div bind:this={scrollContainer} class="flex-1 overflow-y-auto">
    <div class="max-w-5xl mx-auto px-4 py-4">
      {#if chat.messages.length === 0}
        <div class="text-center mt-12 mb-8 px-4">
          <div class="text-5xl mb-4">{currentModuleMeta.emoji}</div>
          <h2 class="text-xl font-semibold text-grey-800 mb-2">
            Bonjour 👋
          </h2>
          <p class="text-sm text-grey-600 max-w-md mx-auto">
            Module <strong class="text-grey-800">{currentModuleMeta.label}</strong> sélectionné. Posez votre question ci-dessous, je m'appuie sur la base documentaire ALISFA pour vous répondre.
          </p>
          <div class="mt-6 grid sm:grid-cols-2 gap-2 max-w-2xl mx-auto text-left">
            {#each SUGGESTIONS[chat.module] as suggestion}
              <button
                class="bg-white {suggestionHoverClass} border border-grey-200 rounded-lg p-3 text-sm text-grey-700 transition cursor-pointer leading-snug"
                onclick={() => handleSend(suggestion)}
              >
                {suggestion}
              </button>
            {/each}
          </div>
        </div>
      {:else}
        {#each chat.messages as message, i (message.id)}
          <MessageBubble
            {message}
            questionForFeedback={message.role === 'assistant' ? questionFor(i) : undefined}
          />
        {/each}
      {/if}
    </div>
  </div>

  <InputBar disabled={busy} onSend={handleSend} />
</div>
