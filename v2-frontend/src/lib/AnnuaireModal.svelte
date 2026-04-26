<script lang="ts">
  // Sprint 4.6 F6 Phase 1 — Annuaire d'orientation
  // 3 onglets : Mon problème (orientations) / Ma région / Tous les acteurs
  import type { Acteur, OrientationSummary, OrientationDetail, RegionInfo } from './types';
  import { fetchOrientations, fetchOrientationDetail, fetchRegions, fetchActeurs } from './api';

  interface Props {
    open: boolean;
    onClose: () => void;
  }
  let { open, onClose }: Props = $props();

  type Tab = 'orientation' | 'region' | 'acteurs';
  let activeTab = $state<Tab>('orientation');

  // Données chargées paresseusement (1 fetch par onglet)
  let orientations = $state<OrientationSummary[] | null>(null);
  let orientationDetail = $state<OrientationDetail | null>(null);
  let regions = $state<RegionInfo[] | null>(null);
  let selectedRegion = $state<string | null>(null);
  let acteurs = $state<Acteur[] | null>(null);
  let acteursFilter = $state<string>('');
  let loading = $state(false);
  let error = $state<string | null>(null);

  $effect(() => {
    if (!open) return;
    void loadCurrentTab();
  });

  $effect(() => {
    void loadCurrentTab();
  });

  async function loadCurrentTab() {
    if (!open) return;
    error = null;
    try {
      if (activeTab === 'orientation' && orientations === null) {
        loading = true;
        orientations = await fetchOrientations();
      } else if (activeTab === 'region' && regions === null) {
        loading = true;
        regions = await fetchRegions();
      } else if (activeTab === 'acteurs' && acteurs === null) {
        loading = true;
        acteurs = await fetchActeurs();
      }
    } catch (e) {
      error = e instanceof Error ? e.message : 'Erreur';
    } finally {
      loading = false;
    }
  }

  async function selectOrientation(id: string) {
    error = null;
    loading = true;
    try {
      orientationDetail = await fetchOrientationDetail(id);
    } catch (e) {
      error = e instanceof Error ? e.message : 'Erreur';
    } finally {
      loading = false;
    }
  }

  function backToOrientations() {
    orientationDetail = null;
  }

  function onKeyDown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      if (orientationDetail) {
        backToOrientations();
      } else {
        onClose();
      }
    }
  }

  // Filtre acteurs (recherche)
  let filteredActeurs = $derived(() => {
    if (!acteurs) return [];
    const q = acteursFilter.trim().toLowerCase();
    if (!q) return acteurs;
    return acteurs.filter(
      (a) =>
        a.nom.toLowerCase().includes(q) ||
        a.role.toLowerCase().includes(q) ||
        (a.description ?? '').toLowerCase().includes(q),
    );
  });

  let selectedRegionInfo = $derived(
    regions?.find((r) => r.region === selectedRegion) ?? null,
  );

  // Couleur badge par type acteur
  const TYPE_BADGES: Record<Acteur['type'], { label: string; className: string }> = {
    elisfa: { label: 'ELISFA', className: 'bg-blue-50 text-blue-700 border-blue-200' },
    federation: { label: 'Fédération', className: 'bg-purple-50 text-purple-700 border-purple-200' },
    syndicat: { label: 'Syndicat', className: 'bg-blue-50 text-blue-700 border-blue-200' },
    opco: { label: 'OPCO', className: 'bg-orange-50 text-orange-700 border-orange-200' },
    institutionnel: { label: 'Institution', className: 'bg-grey-100 text-grey-700 border-grey-200' },
    operateur: { label: 'Opérateur', className: 'bg-green-50 text-green-700 border-green-200' },
    partenaire: { label: 'Partenaire', className: 'bg-grey-100 text-grey-700 border-grey-200' },
    ressource: { label: 'Ressource', className: 'bg-grey-100 text-grey-600 border-grey-200' },
  };
</script>

<svelte:window onkeydown={onKeyDown} />

{#snippet acteurCard(a: Acteur)}
  {@const badge = TYPE_BADGES[a.type]}
  <div class="bg-white border border-grey-200 rounded-lg p-3 hover:border-grey-300 hover:shadow-sm transition">
    <div class="flex items-start justify-between gap-2 mb-1">
      <h4 class="font-semibold text-sm text-navy-900 leading-snug">{a.nom}</h4>
      <span class="shrink-0 text-[10px] uppercase font-bold tracking-wider rounded px-1.5 py-0.5 border {badge.className}">
        {badge.label}
      </span>
    </div>
    <p class="text-xs font-medium text-grey-700 mb-1">{a.role}</p>
    {#if a.description}
      <p class="text-xs text-grey-600 leading-relaxed">{a.description}</p>
    {/if}
    {#if a.email || a.phone || a.url}
      <div class="mt-2 flex flex-wrap gap-2 text-xs">
        {#if a.email}
          <a href={`mailto:${a.email}`} class="text-blue-600 hover:underline">✉ {a.email}</a>
        {/if}
        {#if a.phone}
          <a href={`tel:${a.phone.replace(/\s/g, '')}`} class="text-blue-600 hover:underline">📞 {a.phone}</a>
        {/if}
        {#if a.url}
          <a href={a.url} target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:underline">
            🔗 {a.url.replace(/^https?:\/\//, '').replace(/\/$/, '')}
          </a>
        {/if}
      </div>
    {/if}
  </div>
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
      aria-labelledby="annuaire-title"
      tabindex="-1"
      onclick={(e) => e.stopPropagation()}
    >
      <!-- Header -->
      <div class="bg-gradient-to-r from-navy-900 to-navy-700 text-white px-5 py-3 flex items-center justify-between">
        <div>
          <h2 id="annuaire-title" class="font-semibold text-base flex items-center gap-2">
            <span>🏛</span>
            <span>Annuaire d'orientation ALISFA</span>
          </h2>
          <p class="text-[11px] sm:text-xs text-white/70 mt-0.5">
            Trouver le bon interlocuteur selon votre situation
          </p>
        </div>
        <button
          class="text-white/80 hover:text-white text-xl leading-none cursor-pointer w-7 h-7 flex items-center justify-center rounded-md hover:bg-white/10"
          onclick={onClose}
          aria-label="Fermer"
        >×</button>
      </div>

      <!-- Tabs -->
      <div class="border-b border-grey-200 bg-grey-50 px-3 sm:px-4 flex gap-1 overflow-x-auto">
        <button
          class="text-xs sm:text-sm py-2.5 px-3 cursor-pointer whitespace-nowrap transition border-b-2 {activeTab === 'orientation' ? 'border-blue-600 text-blue-700 font-semibold' : 'border-transparent text-grey-600 hover:text-grey-800'}"
          onclick={() => { activeTab = 'orientation'; orientationDetail = null; }}
        >🎯 Mon problème</button>
        <button
          class="text-xs sm:text-sm py-2.5 px-3 cursor-pointer whitespace-nowrap transition border-b-2 {activeTab === 'region' ? 'border-blue-600 text-blue-700 font-semibold' : 'border-transparent text-grey-600 hover:text-grey-800'}"
          onclick={() => { activeTab = 'region'; selectedRegion = null; }}
        >📍 Ma région</button>
        <button
          class="text-xs sm:text-sm py-2.5 px-3 cursor-pointer whitespace-nowrap transition border-b-2 {activeTab === 'acteurs' ? 'border-blue-600 text-blue-700 font-semibold' : 'border-transparent text-grey-600 hover:text-grey-800'}"
          onclick={() => { activeTab = 'acteurs'; }}
        >📚 Tous les acteurs</button>
      </div>

      <!-- Body -->
      <div class="flex-1 overflow-y-auto px-5 py-4">
        {#if loading}
          <p class="text-sm text-grey-500 py-8 text-center">Chargement…</p>
        {:else if error}
          <p class="text-sm text-red-600 py-4">⚠️ {error}</p>
        {:else if activeTab === 'orientation'}
          {#if orientationDetail}
            <!-- Vue détail orientation -->
            <button
              class="text-xs text-grey-600 hover:text-grey-900 mb-3 cursor-pointer"
              onclick={backToOrientations}
            >← Retour aux orientations</button>
            <div class="mb-4">
              <h3 class="text-base font-semibold text-navy-900 flex items-center gap-2">
                <span class="text-xl">{orientationDetail.icon}</span>
                <span>{orientationDetail.label}</span>
              </h3>
              <p class="text-xs text-grey-600 mt-1 leading-relaxed">{orientationDetail.description}</p>
            </div>
            <p class="text-[11px] uppercase tracking-wider font-bold text-grey-500 mb-2">
              Qui contacter (par ordre de priorité)
            </p>
            <div class="flex flex-col gap-2">
              {#each orientationDetail.acteurs as a}
                {@render acteurCard(a)}
              {/each}
            </div>
          {:else if orientations}
            <p class="text-xs text-grey-600 mb-3">
              Choisissez la nature de votre situation. Vous obtiendrez la liste des
              interlocuteurs à contacter, dans l'ordre de priorité.
            </p>
            <div class="grid sm:grid-cols-2 gap-2">
              {#each orientations as o}
                <button
                  type="button"
                  class="text-left bg-white border border-grey-200 hover:border-blue-400 hover:bg-blue-50 rounded-lg p-3 cursor-pointer transition"
                  onclick={() => selectOrientation(o.id)}
                >
                  <div class="flex items-start gap-2.5">
                    <span class="text-xl shrink-0">{o.icon}</span>
                    <div class="min-w-0">
                      <div class="font-semibold text-sm text-navy-900 leading-snug mb-0.5">{o.label}</div>
                      <div class="text-xs text-grey-600 leading-snug">{o.description}</div>
                      <div class="text-[10px] uppercase tracking-wider text-blue-600 font-bold mt-1">
                        {o.n_acteurs} interlocuteur{o.n_acteurs > 1 ? 's' : ''}
                      </div>
                    </div>
                  </div>
                </button>
              {/each}
            </div>
          {/if}

        {:else if activeTab === 'region'}
          {#if selectedRegionInfo}
            <button
              class="text-xs text-grey-600 hover:text-grey-900 mb-3 cursor-pointer"
              onclick={() => (selectedRegion = null)}
            >← Retour aux régions</button>
            <h3 class="text-base font-semibold text-navy-900 flex items-center gap-2 mb-3">
              <span>📍</span>
              <span>{selectedRegionInfo.region}</span>
            </h3>
            <div class="bg-white border-2 border-blue-300 rounded-lg p-3 mb-4">
              <div class="text-[10px] uppercase tracking-wider font-bold text-blue-600 mb-1">
                Votre référent ELISFA
              </div>
              <p class="text-sm text-navy-900 font-medium">{selectedRegionInfo.elisfa_referent}</p>
            </div>
            {#if selectedRegionInfo.fcsf_federations.length > 0}
              <div class="mb-4">
                <h4 class="text-[11px] uppercase tracking-wider font-bold text-green-700 mb-2 flex items-center gap-1">
                  <span>🏠</span> Fédérations FCSF (centres sociaux)
                </h4>
                <ul class="text-xs text-grey-700 space-y-1 pl-1">
                  {#each selectedRegionInfo.fcsf_federations as f}
                    <li class="border-b border-grey-100 py-1">• {f}</li>
                  {/each}
                </ul>
              </div>
            {/if}
            {#if selectedRegionInfo.acepp_federations.length > 0}
              <div>
                <h4 class="text-[11px] uppercase tracking-wider font-bold text-purple-700 mb-2 flex items-center gap-1">
                  <span>🍼</span> Fédérations ACEPP (petite enfance)
                </h4>
                <ul class="text-xs text-grey-700 space-y-1 pl-1">
                  {#each selectedRegionInfo.acepp_federations as f}
                    <li class="border-b border-grey-100 py-1">• {f}</li>
                  {/each}
                </ul>
              </div>
            {/if}
            {#if selectedRegionInfo.fcsf_federations.length === 0 && selectedRegionInfo.acepp_federations.length === 0}
              <p class="text-xs text-grey-500 italic">
                Pas de fédération régionale référencée. Contactez directement votre référent ELISFA ci-dessus.
              </p>
            {/if}
          {:else if regions}
            <p class="text-xs text-grey-600 mb-3">
              Choisissez votre région pour obtenir votre référent ELISFA + fédérations
              partenaires (FCSF / ACEPP).
            </p>
            <div class="grid sm:grid-cols-2 gap-2">
              {#each regions as r}
                {@const total = r.fcsf_federations.length + r.acepp_federations.length}
                <button
                  type="button"
                  class="text-left bg-white border border-grey-200 hover:border-blue-400 hover:bg-blue-50 rounded-lg p-3 cursor-pointer transition flex items-center justify-between"
                  onclick={() => (selectedRegion = r.region)}
                >
                  <span class="font-medium text-sm text-navy-900">🏛 {r.region}</span>
                  <span class="text-[10px] text-grey-500">
                    {total > 0 ? `${total} fédération${total > 1 ? 's' : ''}` : 'ELISFA direct'}
                  </span>
                </button>
              {/each}
            </div>
          {/if}

        {:else if activeTab === 'acteurs'}
          <input
            type="search"
            placeholder="Rechercher un acteur (nom, rôle, mots-clés)…"
            class="w-full mb-3 text-sm border border-grey-300 rounded-md px-3 py-2 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none"
            value={acteursFilter}
            oninput={(e) => (acteursFilter = (e.target as HTMLInputElement).value)}
          />
          {#if filteredActeurs().length === 0}
            <p class="text-xs text-grey-500 italic py-4 text-center">Aucun acteur trouvé.</p>
          {:else}
            <p class="text-[11px] text-grey-500 mb-2">
              {filteredActeurs().length} acteur{filteredActeurs().length > 1 ? 's' : ''}
            </p>
            <div class="flex flex-col gap-2">
              {#each filteredActeurs() as a}
                {@render acteurCard(a)}
              {/each}
            </div>
          {/if}
        {/if}
      </div>
    </div>
  </div>
{/if}
