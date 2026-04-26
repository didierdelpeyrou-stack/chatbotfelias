<script lang="ts">
  import { chat, addMessage, updateMessage, newId } from './store.svelte';
  import { askStream, askOnce } from './api';
  import { MODULES } from './types';
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

  async function handleSend(text: string) {
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
    addMessage({
      id: assistantId,
      role: 'assistant',
      content: '',
      module: chat.module,
      pending: true,
    });

    try {
      // Phase 2 : streaming SSE — sources reçues d'abord, puis tokens progressifs.
      let answerSoFar = '';
      let receivedAnyEvent = false;

      try {
        await askStream({ question: text, module: chat.module }, (event) => {
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
          const res = await askOnce({ question: text, module: chat.module });
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
          <div class="mt-6 grid sm:grid-cols-2 gap-2 max-w-xl mx-auto text-left">
            {#if chat.module === 'juridique'}
              <button class="bg-white hover:bg-blue-50 border border-grey-200 rounded-lg p-3 text-sm text-grey-700 transition cursor-pointer" onclick={() => handleSend('Quelle est la durée de la période d\'essai en CDI ?')}>
                Durée de la période d'essai en CDI ?
              </button>
              <button class="bg-white hover:bg-blue-50 border border-grey-200 rounded-lg p-3 text-sm text-grey-700 transition cursor-pointer" onclick={() => handleSend('Comment fonctionne le RSAI en EAJE ?')}>
                Comment fonctionne le RSAI en EAJE ?
              </button>
            {:else if chat.module === 'formation'}
              <button class="bg-white hover:bg-orange-50 border border-grey-200 rounded-lg p-3 text-sm text-grey-700 transition cursor-pointer" onclick={() => handleSend('Comment financer une formation BAFA ?')}>
                Comment financer une formation BAFA ?
              </button>
              <button class="bg-white hover:bg-orange-50 border border-grey-200 rounded-lg p-3 text-sm text-grey-700 transition cursor-pointer" onclick={() => handleSend('Qu\'est-ce que le CPF de transition ?')}>
                Qu'est-ce que le CPF de transition ?
              </button>
            {:else if chat.module === 'rh'}
              <button class="bg-white hover:bg-green-50 border border-grey-200 rounded-lg p-3 text-sm text-grey-700 transition cursor-pointer" onclick={() => handleSend('Combien d\'emplois repères dans la branche ALISFA ?')}>
                Les 15 emplois repères ALISFA ?
              </button>
              <button class="bg-white hover:bg-green-50 border border-grey-200 rounded-lg p-3 text-sm text-grey-700 transition cursor-pointer" onclick={() => handleSend('Comment calculer une indemnité de licenciement ?')}>
                Calcul indemnité licenciement ?
              </button>
            {:else}
              <button class="bg-white hover:bg-navy-100 border border-grey-200 rounded-lg p-3 text-sm text-grey-700 transition cursor-pointer" onclick={() => handleSend('Quelles obligations RGPD pour mon association ?')}>
                Obligations RGPD pour mon asso ?
              </button>
              <button class="bg-white hover:bg-navy-100 border border-grey-200 rounded-lg p-3 text-sm text-grey-700 transition cursor-pointer" onclick={() => handleSend('Comment fonctionne une CPO avec une mairie ?')}>
                CPO avec une mairie ?
              </button>
            {/if}
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
