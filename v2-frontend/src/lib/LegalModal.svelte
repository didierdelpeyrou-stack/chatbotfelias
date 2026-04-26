<script lang="ts">
  interface Props {
    open: boolean;
    onClose: () => void;
  }
  let { open, onClose }: Props = $props();

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
      class="bg-white max-w-2xl w-full max-h-[85vh] overflow-y-auto rounded-xl shadow-xl"
      role="dialog"
      aria-modal="true"
      aria-labelledby="legal-title"
      tabindex="-1"
      onclick={(e) => e.stopPropagation()}
    >
      <div class="sticky top-0 bg-gradient-to-r from-navy-900 to-navy-700 text-white px-5 py-3 flex items-center justify-between rounded-t-xl">
        <h2 id="legal-title" class="font-semibold text-base">Mentions légales & RGPD</h2>
        <button
          class="text-white/80 hover:text-white text-xl leading-none cursor-pointer w-7 h-7 flex items-center justify-center rounded-md hover:bg-white/10"
          onclick={onClose}
          aria-label="Fermer"
        >×</button>
      </div>

      <div class="px-5 py-4 prose prose-sm max-w-none prose-headings:mt-4 prose-headings:mb-2 prose-p:my-2">
        <h3>À propos de l'outil</h3>
        <p>
          <strong>Chatbot ELISFA</strong> est un assistant informatif basé sur l'intelligence artificielle
          (modèle <em>Claude</em> d'Anthropic) couplé à une base documentaire propre à la branche ALISFA
          (Centres sociaux, EAJE associatifs, accueils de loisirs — IDCC 1261).
        </p>
        <p>
          Il est destiné aux <strong>directions, administrateurs bénévoles, gestionnaires RH</strong>
          des structures de la branche pour s'orienter sur leurs questions juridiques, formation, RH
          et gouvernance.
        </p>

        <h3>Caractère informatif</h3>
        <p>
          Les réponses fournies <strong>n'ont pas valeur de conseil juridique</strong>. Pour toute décision
          engageant la structure, consultez vos statuts, votre expert-comptable, votre commissaire aux
          comptes, le conseil juridique de votre fédération (FCSF, ACEPP, ELISFA) ou un avocat spécialisé.
        </p>
        <p>
          La base documentaire est mise à jour régulièrement mais peut comporter des informations
          obsolètes. <strong>Vérifiez toujours la date de la dernière révision</strong> sur Légifrance,
          le BOFiP, ou auprès de l'autorité compétente avant d'agir.
        </p>

        <h3>Données personnelles (RGPD)</h3>
        <p>
          <strong>Aucune donnée personnelle</strong> n'est conservée durablement par cet outil. Les
          questions sont transmises au modèle <em>Claude</em> (Anthropic, hébergé en UE/USA selon le
          plan) pour traitement et ne sont pas réutilisées pour entraîner le modèle.
        </p>
        <p>
          Les <strong>feedbacks 👍/👎</strong> sont conservés de manière anonyme pour améliorer la
          base documentaire (date, module, note, question, début de réponse) — aucune information
          permettant d'identifier l'utilisateur n'est stockée.
        </p>
        <p>
          La conversation est conservée <strong>localement dans votre navigateur</strong>
          (localStorage) jusqu'à ce que vous cliquiez sur « Nouvelle conversation ». Aucune donnée
          n'est transmise à un tiers en dehors d'Anthropic pour le traitement de la requête.
        </p>

        <h3>Sources et citations</h3>
        <p>
          Les réponses citent les articles de la base documentaire ALISFA via des références
          <code>[ART_xxx]</code> consultables dans le panneau « sources » sous chaque réponse. Les
          fondements juridiques (Code du travail, CCN, jurisprudence) sont précisés explicitement
          quand applicable.
        </p>

        <h3>Éditeur</h3>
        <p>
          Cet outil est édité dans le cadre du programme <strong>FELIAS</strong> en partenariat
          avec <strong>ELISFA</strong> (Employeurs de la branche ALISFA — 1, rue Cabanis 75014 Paris,
          tél. 01 58 46 13 40, <a href="https://www.elisfa.fr" target="_blank" rel="noopener">elisfa.fr</a>).
        </p>
        <p>
          Pour toute question, suggestion ou signalement d'erreur, contactez votre fédération
          (FCSF, ACEPP) ou directement <a href="mailto:contact@elisfa.fr">contact@elisfa.fr</a>.
        </p>
      </div>

      <div class="sticky bottom-0 bg-grey-50 border-t border-grey-200 px-5 py-3 flex justify-end rounded-b-xl">
        <button
          class="bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg px-4 py-2 cursor-pointer transition"
          onclick={onClose}
        >
          J'ai compris
        </button>
      </div>
    </div>
  </div>
{/if}
