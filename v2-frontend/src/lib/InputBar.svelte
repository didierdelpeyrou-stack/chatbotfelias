<script lang="ts">
  interface Props {
    disabled?: boolean;
    onSend: (text: string) => void;
  }

  let { disabled = false, onSend }: Props = $props();

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
    // Entrée sans shift = envoyer ; shift+entrée = nouvelle ligne
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }
</script>

<div class="border-t border-grey-200 bg-white">
  <div class="max-w-5xl mx-auto px-4 py-3">
    <div class="flex items-end gap-2 bg-white border border-grey-300 rounded-xl px-3 py-2 focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-500/20 transition">
      <textarea
        bind:this={textarea}
        rows="1"
        placeholder="Posez votre question…"
        class="flex-1 resize-none outline-none text-sm leading-relaxed bg-transparent placeholder:text-grey-400 max-h-44 overflow-y-auto"
        value={value}
        disabled={disabled}
        oninput={handleInput}
        onkeydown={onKeyDown}
      ></textarea>
      <button
        class="self-end shrink-0 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold px-3.5 py-2 transition cursor-pointer disabled:bg-grey-300 disabled:cursor-not-allowed"
        disabled={disabled || !value.trim()}
        onclick={send}
        title="Envoyer (Entrée)"
      >
        Envoyer
      </button>
    </div>
    <p class="mt-1.5 text-[11px] text-grey-400 text-center">
      Entrée pour envoyer · Shift+Entrée pour aller à la ligne · Outil informatif, pas un conseil juridique
    </p>
  </div>
</div>
