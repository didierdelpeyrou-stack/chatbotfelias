<script lang="ts">
  // Sprint 4.6 F5 — Bibliothèque des 25 fiches métiers CPNEF ALISFA
  // Source : alisfa.fr/emploi-et-formation/gpec/ + API JobMap Cognito.
  // Toutes les fiches sont des PDF officiels téléchargeables sur alisfa.fr.
  import type { DocAnnexe, FamilleMetier, FicheMetier } from './types';
  import { fetchFichesMetiers } from './api';

  interface Props {
    open: boolean;
    onClose: () => void;
  }
  let { open, onClose }: Props = $props();

  let familles = $state<FamilleMetier[] | null>(null);
  let docsAnnexes = $state<DocAnnexe[]>([]);
  let total = $state(0);
  let loading = $state(false);
  let error = $state<string | null>(null);
  let filter = $state('');
  let activeFamilleId = $state<string | null>(null);

  $effect(() => {
    if (!open || familles !== null) return;
    void load();
  });

  async function load() {
    error = null;
    loading = true;
    try {
      const r = await fetchFichesMetiers();
      familles = r.familles;
      docsAnnexes = r.docs_annexes;
      total = r.total;
    } catch (e) {
      error = e instanceof Error ? e.message : 'Erreur';
    } finally {
      loading = false;
    }
  }

  function onKeyDown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      if (activeFamilleId) {
        activeFamilleId = null;
      } else if (filter) {
        filter = '';
      } else {
        onClose();
      }
    }
  }

  // Recherche cross-famille
  let allFiches = $derived<FicheMetier[]>(
    familles?.flatMap((f) => f.fiches) ?? [],
  );

  let filteredFiches = $derived(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return [];
    return allFiches.filter(
      (f) =>
        f.nom.toLowerCase().includes(q) ||
        f.description.toLowerCase().includes(q),
    );
  });

  let activeFamille = $derived<FamilleMetier | null>(
    familles?.find((f) => f.id === activeFamilleId) ?? null,
  );

  function familleLabel(id: string): string {
    return familles?.find((f) => f.id === id)?.label ?? id;
  }
</script>

<svelte:window onkeydown={onKeyDown} />

{#snippet ficheCard(f: FicheMetier, showFamille: boolean = false)}
  <a
    href={f.pdf_url}
    target="_blank"
    rel="noopener noreferrer"
    class="block bg-white border border-grey-200 rounded-lg p-3 hover:border-blue-400 hover:bg-blue-50 hover:shadow-sm transition group"
  >
    <div class="flex items-start gap-2">
      <span class="shrink-0 text-xl">📄</span>
      <div class="flex-1 min-w-0">
        <h4 class="font-semibold text-sm text-navy-900 leading-snug group-hover:text-blue-700 mb-0.5">
          {f.nom}
        </h4>
        {#if showFamille}
          <p class="text-[10px] uppercase tracking-wider text-grey-500 mb-1">
            {familleLabel(f.famille_id)}
          </p>
        {/if}
        <p class="text-xs text-grey-600 leading-relaxed mb-1.5">{f.description}</p>
        <span class="text-[11px] text-blue-600 font-medium inline-flex items-center gap-1">
          ↓ Télécharger la fiche PDF (alisfa.fr)
        </span>
      </div>
    </div>
  </a>
{/snippet}

{#if open}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4"
    onclick={onClose}
  >
    <div
      class="bg-white max-w-3xl w-full max-h-[92vh] overflow-hidden rounded-xl shadow-xl flex flex-col"
      role="dialog"
      aria-modal="true"
      aria-labelledby="fiches-title"
      tabindex="-1"
      onclick={(e) => e.stopPropagation()}
    >
      <!-- Header -->
      <div class="bg-gradient-to-r from-orange-700 to-orange-500 text-white px-5 py-3 flex items-center justify-between">
        <div>
          <h2 id="fiches-title" class="font-semibold text-base flex items-center gap-2">
            <span>📄</span>
            <span>Fiches métiers CPNEF ALISFA</span>
          </h2>
          <p class="text-[11px] sm:text-xs text-white/80 mt-0.5">
            25 fiches métiers officielles · 5 familles · PDF téléchargeables
          </p>
        </div>
        <button
          class="text-white/80 hover:text-white text-xl leading-none cursor-pointer w-7 h-7 flex items-center justify-center rounded-md hover:bg-white/10"
          onclick={onClose}
          aria-label="Fermer"
        >×</button>
      </div>

      <!-- Body -->
      <div class="flex-1 overflow-y-auto px-5 py-4">
        {#if loading}
          <p class="text-sm text-grey-500 py-8 text-center">Chargement…</p>
        {:else if error}
          <p class="text-sm text-red-600 py-4">⚠️ {error}</p>
        {:else if familles}
          <!-- Recherche -->
          <input
            type="search"
            placeholder="Rechercher un métier (nom, mission)…"
            class="w-full mb-4 text-sm border border-grey-300 rounded-md px-3 py-2 focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20 outline-none"
            value={filter}
            oninput={(e) => {
              filter = (e.target as HTMLInputElement).value;
              activeFamilleId = null;
            }}
          />

          {#if filter.trim()}
            <!-- Résultats de recherche -->
            {#if filteredFiches().length === 0}
              <p class="text-xs text-grey-500 italic py-4 text-center">
                Aucun métier ne correspond à « {filter} ».
              </p>
            {:else}
              <p class="text-[11px] text-grey-500 mb-3">
                {filteredFiches().length} résultat{filteredFiches().length > 1 ? 's' : ''}
              </p>
              <div class="flex flex-col gap-2">
                {#each filteredFiches() as f (f.id)}
                  {@render ficheCard(f, true)}
                {/each}
              </div>
            {/if}

          {:else if activeFamille}
            <!-- Vue famille -->
            <button
              class="text-xs text-grey-600 hover:text-grey-900 mb-3 cursor-pointer"
              onclick={() => (activeFamilleId = null)}
            >← Toutes les familles</button>
            <div class="mb-4">
              <h3 class="text-base font-semibold text-navy-900 flex items-center gap-2">
                <span class="text-xl">{activeFamille.icon}</span>
                <span>{activeFamille.label}</span>
              </h3>
              <p class="text-xs text-grey-600 mt-1 leading-relaxed">
                {activeFamille.description}
              </p>
            </div>
            <div class="flex flex-col gap-2">
              {#each activeFamille.fiches as f (f.id)}
                {@render ficheCard(f)}
              {/each}
            </div>

          {:else}
            <!-- Vue par famille -->
            <p class="text-xs text-grey-600 mb-3">
              Cartographie GPEC ALISFA : {total} fiches métiers officielles
              produites par la CPNEF, organisées en 5 familles. Cliquez sur
              une famille pour voir ses métiers, ou utilisez la recherche.
            </p>

            <div class="grid sm:grid-cols-2 gap-2 mb-5">
              {#each familles as fam (fam.id)}
                <button
                  type="button"
                  class="text-left bg-white border border-grey-200 hover:border-orange-400 hover:bg-orange-50 rounded-lg p-3 cursor-pointer transition"
                  onclick={() => (activeFamilleId = fam.id)}
                >
                  <div class="flex items-start gap-2.5">
                    <span class="text-xl shrink-0">{fam.icon}</span>
                    <div class="min-w-0">
                      <div class="font-semibold text-sm text-navy-900 leading-snug mb-0.5">
                        {fam.label}
                      </div>
                      <div class="text-xs text-grey-600 leading-snug">{fam.description}</div>
                      <div class="text-[10px] uppercase tracking-wider text-orange-600 font-bold mt-1">
                        {fam.fiches.length} fiche{fam.fiches.length > 1 ? 's' : ''}
                      </div>
                    </div>
                  </div>
                </button>
              {/each}
            </div>

            {#if docsAnnexes.length > 0}
              <h3 class="text-[11px] uppercase tracking-wider font-bold text-grey-600 mb-2 mt-4 border-t border-grey-100 pt-4">
                📚 Documents transverses CPNEF
              </h3>
              <p class="text-xs text-grey-600 mb-3">
                Ressources complémentaires : panorama de branche, guide
                entretien professionnel, brochures égalité…
              </p>
              <div class="flex flex-col gap-2">
                {#each docsAnnexes as d (d.id)}
                  <a
                    href={d.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    class="block bg-white border border-grey-200 rounded-lg p-3 hover:border-orange-400 hover:bg-orange-50 transition group"
                  >
                    <div class="flex items-start gap-2">
                      <span class="shrink-0 text-lg">📑</span>
                      <div class="flex-1 min-w-0">
                        <h4 class="font-semibold text-sm text-navy-900 leading-snug group-hover:text-orange-700 mb-0.5">
                          {d.label}
                        </h4>
                        <p class="text-xs text-grey-600 leading-relaxed">{d.description}</p>
                      </div>
                    </div>
                  </a>
                {/each}
              </div>
            {/if}

            <p class="text-[11px] text-grey-500 mt-5 italic leading-relaxed">
              Sources : Commission Paritaire Nationale Emploi Formation
              (CPNEF) ALISFA, cartographie GPEC publiée sur
              <a
                href="https://www.alisfa.fr/emploi-et-formation/gpec/"
                target="_blank"
                rel="noopener noreferrer"
                class="text-blue-600 hover:underline"
              >alisfa.fr/emploi-et-formation/gpec</a>.
            </p>
          {/if}
        {/if}
      </div>
    </div>
  </div>
{/if}
