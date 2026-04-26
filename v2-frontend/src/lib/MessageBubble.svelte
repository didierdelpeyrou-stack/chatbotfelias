<script lang="ts">
  import type { ChatMessage } from './types';
  import { renderMarkdown } from './markdown';
  import { updateMessage } from './store.svelte';
  import { postFeedback } from './api';

  interface Props {
    message: ChatMessage;
    questionForFeedback?: string;
  }

  let { message, questionForFeedback }: Props = $props();

  let html = $derived(renderMarkdown(message.content));
  let showSources = $state(false);

  async function rate(value: 1 | -1) {
    if (message.rating || !questionForFeedback || !message.module) return;
    updateMessage(message.id, { rating: value });
    try {
      await postFeedback({
        rating: value,
        question: questionForFeedback,
        answer: message.content,
        module: message.module,
      });
    } catch (e) {
      // En cas d'erreur, on garde le rating local pour ne pas frustrer l'utilisateur
      console.error('feedback failed', e);
    }
  }
</script>

{#if message.role === 'user'}
  <div class="flex justify-end mb-3">
    <div class="max-w-[85%] bg-blue-600 text-white rounded-2xl rounded-br-sm px-4 py-2.5 shadow-sm">
      <p class="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
    </div>
  </div>
{:else}
  <div class="flex flex-col items-start mb-4">
    <div class="max-w-[92%] bg-white border border-grey-200 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
      {#if message.error}
        <div class="text-sm text-red-600 flex items-start gap-2">
          <span>⚠️</span>
          <div>
            <p class="font-semibold">Erreur</p>
            <p class="text-xs text-grey-600 mt-0.5">{message.error}</p>
          </div>
        </div>
      {:else if message.pending && !message.content}
        <div class="flex items-center gap-1.5 py-1">
          <span class="w-1.5 h-1.5 rounded-full bg-grey-400 animate-bounce" style="animation-delay: 0ms"></span>
          <span class="w-1.5 h-1.5 rounded-full bg-grey-400 animate-bounce" style="animation-delay: 150ms"></span>
          <span class="w-1.5 h-1.5 rounded-full bg-grey-400 animate-bounce" style="animation-delay: 300ms"></span>
        </div>
      {:else}
        <div class="prose prose-sm max-w-none prose-p:my-2 prose-headings:my-3 prose-ul:my-2 prose-li:my-0.5 prose-pre:bg-grey-100 prose-pre:text-grey-800">
          {@html html}
        </div>
        {#if message.hors_corpus}
          <div class="mt-2 text-xs text-orange-600 bg-orange-50 border border-orange-100 rounded-md px-2 py-1.5">
            Cette question semble hors du corpus ALISFA. La réponse peut être moins fiable.
          </div>
        {/if}
      {/if}
    </div>

    {#if !message.pending && !message.error}
      {@const sources = message.sources ?? []}
      <div class="mt-2 flex flex-wrap items-center gap-2 text-xs ml-1">
        {#if sources.length > 0}
          <button
            class="text-grey-600 hover:text-grey-900 cursor-pointer underline-offset-2 hover:underline"
            onclick={() => (showSources = !showSources)}
          >
            {showSources ? '▾' : '▸'} {sources.length} source{sources.length > 1 ? 's' : ''}
          </button>
          <span class="text-grey-300">·</span>
        {/if}
        <button
          class="cursor-pointer transition {message.rating === 1 ? 'text-green-600' : 'text-grey-400 hover:text-green-600'}"
          title="Réponse utile"
          aria-label="J'aime"
          onclick={() => rate(1)}
        >👍</button>
        <button
          class="cursor-pointer transition {message.rating === -1 ? 'text-red-600' : 'text-grey-400 hover:text-red-600'}"
          title="Réponse pas utile"
          aria-label="Je n'aime pas"
          onclick={() => rate(-1)}
        >👎</button>
        {#if message.duration_ms}
          <span class="text-grey-300">·</span>
          <span class="text-grey-400">{(message.duration_ms / 1000).toFixed(1)}s</span>
        {/if}
      </div>

      {#if showSources && sources.length > 0}
        <div class="mt-2 ml-1 flex flex-col gap-1.5 max-w-[92%]">
          {#each sources as src}
            <div class="text-xs bg-grey-50 border border-grey-200 rounded-md px-3 py-2">
              <div class="flex items-baseline gap-2 flex-wrap">
                <span class="font-mono text-grey-700">{src.id ?? '?'}</span>
                <span class="text-grey-500">·</span>
                <span class="text-grey-600">{src.theme_label}</span>
                <span class="text-grey-500">·</span>
                <span class="text-grey-500">score {(src.score_normalized * 100).toFixed(0)}%</span>
              </div>
              {#if src.title}
                <p class="text-grey-700 mt-0.5 leading-snug">{src.title}</p>
              {/if}
            </div>
          {/each}
        </div>
      {/if}
    {/if}
  </div>
{/if}
