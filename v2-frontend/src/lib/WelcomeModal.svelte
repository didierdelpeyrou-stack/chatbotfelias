<script lang="ts">
  // Sprint 4.6 F1.5 + 1.6 — Onboarding : 2 étapes
  //   Étape 1 : sélecteur de profil utilisateur
  //   Étape 2 : caractéristiques de la structure (questions fermées)
  //
  // Affiché auto à la 1re visite (chat.profileId === null).
  // Ré-ouvrable via le chip "profil" du Header.
  import { onMount } from 'svelte';
  import type { ProfileExtras, UserProfile } from './types';
  import { fetchProfiles } from './api';
  import { chat, setProfile, setProfileExtras, clearProfileExtras } from './store.svelte';

  interface Props {
    open: boolean;
    /** Si true, c'est l'onboarding 1re visite (pas de bouton "ignorer"). */
    isOnboarding?: boolean;
    onClose: () => void;
  }
  let { open, isOnboarding = false, onClose }: Props = $props();

  let profiles: UserProfile[] = $state([]);
  let loading = $state(true);

  // Étapes : 1 = choix du profil, 2 = caractéristiques structure
  let step = $state<1 | 2>(1);
  let extras = $state<ProfileExtras>({});

  onMount(async () => {
    try {
      profiles = await fetchProfiles();
    } catch (e) {
      console.error('fetchProfiles failed', e);
    } finally {
      loading = false;
    }
  });

  // À chaque ouverture, reset l'étape et précharge les extras existants
  $effect(() => {
    if (open) {
      step = chat.profileId ? 2 : 1;  // si profil déjà choisi → on va direct à étape 2 (édition)
      extras = { ...chat.profileExtras };
    }
  });

  function pickProfile(p: UserProfile) {
    setProfile(p.id);
    step = 2;
  }

  function goBackToStep1() {
    step = 1;
  }

  function setExtra<K extends keyof ProfileExtras>(key: K, value: ProfileExtras[K]) {
    extras[key] = value;
  }

  function finish() {
    // Persiste les extras + ferme
    setProfileExtras(extras);
    onClose();
  }

  function skipOnboarding() {
    // L'utilisateur ignore l'onboarding (chat libre sans profil)
    setProfile(null);
    clearProfileExtras();
    onClose();
  }

  function clearProfile() {
    // Effacer le profil et fermer (depuis étape 2 d'édition)
    setProfile(null);
    clearProfileExtras();
    onClose();
  }

  function onKeyDown(e: KeyboardEvent) {
    if (e.key === 'Escape' && !isOnboarding) onClose();
  }

  let benevoles = $derived(profiles.filter((p) => p.type === 'benevole'));
  let pros = $derived(profiles.filter((p) => p.type === 'professionnel'));
  let currentProfile = $derived(profiles.find((p) => p.id === chat.profileId) ?? null);

  // Options des questions structure (alignées avec ALLOWED_KEYS du backend)
  const STRUCTURES = [
    { value: 'EAJE / Crèche', label: '🍼 EAJE / Crèche' },
    { value: 'Centre social', label: '🏘 Centre social' },
    { value: 'ALSH / Accueil de loisirs', label: '🎈 ALSH / Accueil de loisirs' },
    { value: 'EVS / Espace de vie sociale', label: '🤝 EVS' },
    { value: 'MJC / Maison des jeunes', label: '🎭 MJC' },
    { value: 'Foyer / Hébergement', label: '🏠 Foyer / Hébergement' },
    { value: 'Autre', label: '✏️ Autre (précisez)' },
  ];
  const HEADCOUNTS = ['Moins de 11', '11 à 49', '50 à 249', '250 et plus'];
  const STATUTS = ['Association loi 1901', 'SCIC', 'Coopérative (autre)', 'Autre'];
  const PUBLICS = [
    'Petite enfance (0–3 ans)',
    'Enfance (3–12 ans)',
    'Jeunesse (12–25 ans)',
    'Adultes',
    'Tous publics',
  ];
  const BENEVOLES = ['Pas de bénévoles', 'Moins de 10', '10 à 50', 'Plus de 50'];
</script>

<svelte:window onkeydown={onKeyDown} />

{#if open}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4"
    onclick={isOnboarding ? undefined : onClose}
  >
    <div
      class="bg-white max-w-3xl w-full max-h-[92vh] overflow-y-auto rounded-xl shadow-xl"
      role="dialog"
      aria-modal="true"
      aria-labelledby="welcome-title"
      tabindex="-1"
      onclick={(e) => e.stopPropagation()}
    >
      <div class="bg-gradient-to-r from-navy-900 to-navy-700 text-white px-5 py-4 rounded-t-xl">
        <h2 id="welcome-title" class="font-semibold text-lg flex items-center gap-2">
          <span>👋</span>
          {#if step === 1}
            <span>{isOnboarding ? 'Bienvenue sur Chatbot ELISFA' : 'Modifier votre profil'}</span>
          {:else}
            <span>Votre structure</span>
          {/if}
        </h2>
        <p class="text-xs sm:text-sm text-white/80 mt-1">
          {#if step === 1}
            Pour adapter les réponses à votre rôle, indiquez-nous qui vous êtes :
          {:else if currentProfile}
            <span class="inline-flex items-center gap-1">
              {currentProfile.icon} {currentProfile.name}
            </span>
            <span class="text-white/60"> — quelques infos pour personnaliser les réponses (toutes optionnelles)</span>
          {/if}
        </p>
      </div>

      {#if step === 1}
        <!-- ── ÉTAPE 1 : Choix du profil ── -->
        <div class="px-5 py-4">
          {#if loading}
            <p class="text-sm text-grey-500 py-8 text-center">Chargement…</p>
          {:else}
            {#if benevoles.length > 0}
              <h3 class="text-xs font-bold uppercase tracking-wider text-grey-500 mb-2">Bénévoles</h3>
              <div class="grid sm:grid-cols-2 gap-2 mb-4">
                {#each benevoles as p}
                  <button
                    type="button"
                    class="text-left bg-white border-2 border-grey-200 hover:border-purple-400 hover:bg-purple-50 rounded-lg p-3 cursor-pointer transition"
                    onclick={() => pickProfile(p)}
                  >
                    <div class="flex items-start gap-2.5">
                      <span class="text-2xl shrink-0">{p.icon}</span>
                      <div class="min-w-0">
                        <div class="font-semibold text-sm text-navy-900 mb-0.5">{p.name}</div>
                        <div class="text-xs text-grey-600 leading-snug">{p.summary}</div>
                      </div>
                    </div>
                  </button>
                {/each}
              </div>
            {/if}

            {#if pros.length > 0}
              <h3 class="text-xs font-bold uppercase tracking-wider text-grey-500 mb-2 mt-2">Professionnels</h3>
              <div class="grid sm:grid-cols-2 gap-2 mb-2">
                {#each pros as p}
                  <button
                    type="button"
                    class="text-left bg-white border-2 border-grey-200 hover:border-blue-500 hover:bg-blue-50 rounded-lg p-3 cursor-pointer transition"
                    onclick={() => pickProfile(p)}
                  >
                    <div class="flex items-start gap-2.5">
                      <span class="text-2xl shrink-0">{p.icon}</span>
                      <div class="min-w-0">
                        <div class="font-semibold text-sm text-navy-900 mb-0.5">{p.name}</div>
                        <div class="text-xs text-grey-600 leading-snug">{p.summary}</div>
                      </div>
                    </div>
                  </button>
                {/each}
              </div>
            {/if}

            <div class="text-center mt-4 pt-3 border-t border-grey-100">
              <button
                type="button"
                class="text-xs text-grey-500 hover:text-grey-700 underline-offset-2 hover:underline cursor-pointer"
                onclick={skipOnboarding}
              >
                Continuer sans profil (chat libre)
              </button>
            </div>
          {/if}
        </div>
      {:else}
        <!-- ── ÉTAPE 2 : Caractéristiques de la structure ── -->
        <div class="px-5 py-4 space-y-5">
          <!-- Type de structure -->
          <fieldset>
            <legend class="text-xs font-bold uppercase tracking-wider text-grey-500 mb-2">
              Type de structure
            </legend>
            <div class="flex flex-wrap gap-1.5">
              {#each STRUCTURES as opt}
                {@const sel = extras.type_structure === opt.value}
                <button
                  type="button"
                  class="text-xs rounded-md px-3 py-1.5 cursor-pointer transition border {sel ? 'bg-blue-50 border-blue-500 text-blue-900 ring-2 ring-blue-500/20' : 'bg-white border-grey-200 text-grey-700 hover:border-grey-300 hover:bg-grey-50'}"
                  onclick={() => setExtra('type_structure', opt.value)}
                >
                  {opt.label}
                </button>
              {/each}
            </div>
            {#if extras.type_structure === 'Autre'}
              <input
                type="text"
                class="mt-2 w-full text-sm border border-grey-300 rounded-md px-3 py-1.5 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none"
                placeholder="Précisez le type de structure"
                value={extras.type_structure_other ?? ''}
                oninput={(e) => setExtra('type_structure_other', (e.target as HTMLInputElement).value)}
                maxlength="100"
              />
            {/if}
          </fieldset>

          <!-- Effectif salariés -->
          <fieldset>
            <legend class="text-xs font-bold uppercase tracking-wider text-grey-500 mb-2">
              Effectif salariés
            </legend>
            <div class="flex flex-wrap gap-1.5">
              {#each HEADCOUNTS as v}
                {@const sel = extras.headcount === v}
                <button
                  type="button"
                  class="text-xs rounded-md px-3 py-1.5 cursor-pointer transition border {sel ? 'bg-blue-50 border-blue-500 text-blue-900 ring-2 ring-blue-500/20' : 'bg-white border-grey-200 text-grey-700 hover:border-grey-300 hover:bg-grey-50'}"
                  onclick={() => setExtra('headcount', v)}
                >
                  {v}
                </button>
              {/each}
            </div>
          </fieldset>

          <!-- Statut juridique -->
          <fieldset>
            <legend class="text-xs font-bold uppercase tracking-wider text-grey-500 mb-2">
              Statut juridique
            </legend>
            <div class="flex flex-wrap gap-1.5">
              {#each STATUTS as v}
                {@const sel = extras.statut_juridique === v}
                <button
                  type="button"
                  class="text-xs rounded-md px-3 py-1.5 cursor-pointer transition border {sel ? 'bg-blue-50 border-blue-500 text-blue-900 ring-2 ring-blue-500/20' : 'bg-white border-grey-200 text-grey-700 hover:border-grey-300 hover:bg-grey-50'}"
                  onclick={() => setExtra('statut_juridique', v)}
                >
                  {v}
                </button>
              {/each}
            </div>
          </fieldset>

          <!-- Public principal -->
          <fieldset>
            <legend class="text-xs font-bold uppercase tracking-wider text-grey-500 mb-2">
              Public principal
            </legend>
            <div class="flex flex-wrap gap-1.5">
              {#each PUBLICS as v}
                {@const sel = extras.public_principal === v}
                <button
                  type="button"
                  class="text-xs rounded-md px-3 py-1.5 cursor-pointer transition border {sel ? 'bg-blue-50 border-blue-500 text-blue-900 ring-2 ring-blue-500/20' : 'bg-white border-grey-200 text-grey-700 hover:border-grey-300 hover:bg-grey-50'}"
                  onclick={() => setExtra('public_principal', v)}
                >
                  {v}
                </button>
              {/each}
            </div>
          </fieldset>

          <!-- Bénévoles -->
          <fieldset>
            <legend class="text-xs font-bold uppercase tracking-wider text-grey-500 mb-2">
              Bénévoles dans la structure
            </legend>
            <div class="flex flex-wrap gap-1.5">
              {#each BENEVOLES as v}
                {@const sel = extras.benevoles === v}
                <button
                  type="button"
                  class="text-xs rounded-md px-3 py-1.5 cursor-pointer transition border {sel ? 'bg-blue-50 border-blue-500 text-blue-900 ring-2 ring-blue-500/20' : 'bg-white border-grey-200 text-grey-700 hover:border-grey-300 hover:bg-grey-50'}"
                  onclick={() => setExtra('benevoles', v)}
                >
                  {v}
                </button>
              {/each}
            </div>
          </fieldset>
        </div>

        <!-- Footer étape 2 -->
        <div class="border-t border-grey-200 px-5 py-3 flex items-center justify-between bg-grey-50 sticky bottom-0">
          <div class="flex gap-3">
            <button
              type="button"
              class="text-xs text-grey-600 hover:text-grey-900 cursor-pointer"
              onclick={goBackToStep1}
            >
              ← Changer de profil
            </button>
            {#if !isOnboarding}
              <span class="text-grey-300">·</span>
              <button
                type="button"
                class="text-xs text-grey-500 hover:text-red-600 cursor-pointer"
                onclick={clearProfile}
              >
                Effacer mon profil
              </button>
            {/if}
          </div>
          <button
            type="button"
            class="bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg px-4 py-2 cursor-pointer transition"
            onclick={finish}
          >
            {Object.values(extras).some((v) => v) ? 'Enregistrer →' : 'Passer →'}
          </button>
        </div>
      {/if}
    </div>
  </div>
{/if}
