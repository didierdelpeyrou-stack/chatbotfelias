<script lang="ts">
  // UX-1 Zen-Gemini — InputBar pill arrondie + send button rond
  // Composition : PillBar (module/mode) en haut + textarea + bouton ▶
  import PillBar from './PillBar.svelte';

  interface Props {
    disabled?: boolean;
    onSend: (text: string) => void;
    onOpenWizard: () => void;
  }
  let { disabled = false, onSend, onOpenWizard }: Props = $props();

  let value = $state('');
  let textarea: HTMLTextAreaElement | undefined = $state();

  function autosize() {
    if (!textarea) return;
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 180) + 'px';
  }

  function handleInput(e: Event) {
    value = (e.target as HTMLTextAreaElement).value;
    autosize();
  }

  function send() {
    const text = value.trim();
    if (!text || disabled) return;
    onSend(text);
    value = '';
    queueMicrotask(autosize);
  }

  function onKeyDown(e: KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }
</script>

<div class="bg-white pb-[env(safe-area-inset-bottom)]">
  <div class="max-w-3xl mx-auto px-3 sm:px-4 pt-2 pb-3">
    <div class="mb-2">
      <PillBar {onOpenWizard} />
    </div>
    <div class="flex items-end gap-2 bg-white border border-grey-300 rounded-3xl pl-4 pr-2 py-2 focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-500/20 shadow-sm transition">
      <textarea
        bind:this={textarea}
        rows="1"
        placeholder="Posez votre question…"
        class="flex-1 resize-none outline-none text-sm leading-relaxed bg-transparent placeholder:text-grey-400 max-h-44 overflow-y-auto py-1.5"
        value={value}
        disabled={disabled}
        oninput={handleInput}
        onkeydown={onKeyDown}
      ></textarea>
      <button
        class="self-end shrink-0 rounded-full bg-blue-600 hover:bg-blue-700 text-white w-9 h-9 flex items-center justify-center transition cursor-pointer disabled:bg-grey-300 disabled:cursor-not-allowed"
        disabled={disabled || !value.trim()}
        onclick={send}
        title="Envoyer (Entrée)"
        aria-label="Envoyer"
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <path d="M2.5 8h11M8.5 3l5 5-5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
    </div>
    <p class="mt-1.5 text-[10px] text-grey-400 text-center px-2 leading-snug">
      Entrée pour envoyer · Outil informatif, pas un conseil juridique
    </p>
  </div>
</div>
