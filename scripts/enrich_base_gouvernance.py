#!/usr/bin/env python3
"""
Enrichit base_gouvernance.json avec des articles clés issus de sources
officielles sur la gouvernance associative :
- Loi du 1er juillet 1901 relative au contrat d'association
- Code du travail, Code général des impôts
- associations.gouv.fr (portail officiel du ministère de l'Intérieur)
- Le Mouvement associatif (https://lemouvementassociatif.org/)
- HCVA — Haut Conseil à la Vie Associative
- France Active / France Générosités
- CNRS (Viviane Tchernonog) pour la statistique

Couvre : CA vs bureau vs AG, responsabilité dirigeants bénévoles,
RGPD et assurance associative, dissolution, RNA et rescrit fiscal,
contrat d'engagement républicain, don et mécénat.

Sauvegarde base_gouvernance.json.bak avant modification.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "base_gouvernance.json"
BAK = ROOT / "data" / "base_gouvernance.json.bak"

ASSOS_GOUV = "https://www.associations.gouv.fr/"
LEGIFRANCE_1901 = "https://www.legifrance.gouv.fr/loda/id/LEGITEXT000006069570/"
MVT_ASSO = "https://lemouvementassociatif.org/"
HCVA = "https://www.associations.gouv.fr/le-haut-conseil-a-la-vie-associative-hcva.html"


NEW_ARTICLES = {
    "cadre_legal": [
        {
            "id": "gv-07",
            "question_type": "Quelle est la responsabilité civile et pénale des dirigeants bénévoles d'association ?",
            "mots_cles": [
                "responsabilité dirigeant", "dirigeant bénévole", "faute de gestion",
                "article 1992 Code civil", "mandataire social", "faute séparable",
                "responsabilité pénale", "association employeur", "assurance RC",
                "dirigeants",
            ],
            "reponse": {
                "synthese": "Les dirigeants bénévoles d'une association (président, trésorier, secrétaire, administrateurs) sont des mandataires sociaux agissant au nom et pour le compte de l'association. Leur responsabilité CIVILE n'est en principe engagée que pour faute séparable de leurs fonctions (faute d'une particulière gravité incompatible avec l'exercice normal du mandat — Cass. com. 20 mai 2003 « Société Seusse »). Leur responsabilité PÉNALE est personnelle et engagée pour les infractions qu'ils commettent directement (abus de confiance, travail dissimulé, manquements à l'hygiène/sécurité, fraude fiscale).",
                "fondement_legal": "Loi du 1er juillet 1901 relative au contrat d'association. Article 1992 du Code civil (responsabilité du mandataire). Article 1240 du Code civil (responsabilité délictuelle générale). Article L121-1 du Code pénal (responsabilité pénale personnelle). Articles 121-2 et 121-3 du Code pénal (responsabilité des personnes morales). Jurisprudence : Cass. com. 20 mai 2003 n° 99-17.092 (faute séparable des fonctions), Cass. crim. 9 décembre 2014 n° 13-85.401 (responsabilité pénale du dirigeant employeur).",
                "fondement_ccn": "Sans objet. La CCN ALISFA concerne les salariés, pas les dirigeants bénévoles. Toutefois le président est souvent l'employeur au sens du Code du travail et porte à ce titre les obligations sociales.",
                "application": "Mesures de prévention : (1) souscrire une assurance Responsabilité Civile des Mandataires Sociaux (RCMS) avec garantie étendue aux dirigeants bénévoles, (2) tenir à jour les PV d'assemblée générale et de conseil d'administration, (3) respecter strictement les statuts et le règlement intérieur, (4) documenter toute décision importante (CR, motivation), (5) ne jamais mélanger patrimoine personnel et associatif, (6) s'assurer que le bilan et le compte de résultat sont approuvés annuellement en AG, (7) former les nouveaux administrateurs.",
                "vigilance": "La responsabilité pénale du président en tant qu'employeur est fréquemment engagée en cas d'accident du travail grave (manquement à l'obligation de sécurité — L4121-1 C. trav.), de travail dissimulé (L8221-1) ou de défaut de déclaration à l'URSSAF. Une délégation de pouvoirs claire, précise et acceptée peut transférer cette responsabilité à un salarié directeur (Cass. crim. 19 février 2019 n° 17-82.793) — encore faut-il qu'il ait l'autorité, la compétence et les moyens. En cas d'insolvabilité de l'association, la responsabilité civile des dirigeants pour insuffisance d'actif peut être engagée (art. L651-2 Code de commerce applicable aux associations).",
                "sources": [
                    "Loi du 1er juillet 1901",
                    "Art. 1992 Code civil",
                    "Art. 121-2 et 121-3 Code pénal",
                    "Cass. com. 20 mai 2003 n° 99-17.092",
                    "Cass. crim. 19 février 2019 n° 17-82.793",
                    "HCVA — guide responsabilité des dirigeants associatifs",
                ],
                "liens": [
                    {"titre": "associations.gouv.fr — responsabilité dirigeants", "url": ASSOS_GOUV + "responsabilite-des-dirigeants.html"},
                    {"titre": "Loi 1901 — Légifrance", "url": LEGIFRANCE_1901},
                    {"titre": "HCVA — publications", "url": HCVA},
                ],
            },
            "fiches_pratiques": [],
        },
        {
            "id": "gv-08",
            "question_type": "Qu'est-ce que le Contrat d'Engagement Républicain (CER) et qui est concerné ?",
            "mots_cles": [
                "contrat engagement républicain", "CER",
                "loi séparatisme", "loi 2021-1109", "subventions publiques",
                "agrément", "décret 2021-1947", "retrait",
                "principes républicains", "associations",
            ],
            "reponse": {
                "synthese": "Le Contrat d'Engagement Républicain (CER), créé par la loi du 24 août 2021 confortant le respect des principes de la République (dite « loi séparatisme »), est une obligation pour toute association ou fondation qui sollicite une subvention publique OU un agrément d'État. Elle doit s'engager, à travers un texte en 7 points, à respecter les principes de liberté, d'égalité, de fraternité, de dignité de la personne humaine, à respecter les symboles de la République, à ne pas remettre en cause le caractère laïque de la France, et à s'abstenir de toute action portant atteinte à l'ordre public.",
                "fondement_legal": "Loi n° 2021-1109 du 24 août 2021 confortant le respect des principes de la République. Article 10-1 de la loi n° 2000-321 du 12 avril 2000 (modifié par la loi 2021-1109). Décret n° 2021-1947 du 31 décembre 2021 approuvant le contrat type. Entrée en vigueur le 1er janvier 2022. Le non-respect du CER peut entraîner le retrait de la subvention ou de l'agrément (article 12 de la loi).",
                "fondement_ccn": "Sans objet pour la gouvernance interne. Les structures ALISFA financées par des subventions publiques (État, collectivités, CAF conventions de prestations de service) sont toutes concernées.",
                "application": "Quand souscrire le CER : (1) lors de toute demande de subvention publique (Cerfa 12156*06 ou équivalent), (2) lors de toute demande d'agrément d'État (agrément jeunesse et éducation populaire, agrément sport, reconnaissance d'utilité publique), (3) lors du renouvellement. Le CER est matériellement intégré au formulaire de demande. L'association doit aussi en informer ses adhérents et le mettre en œuvre concrètement dans son fonctionnement.",
                "vigilance": "Le retrait d'une subvention déjà versée en cas de non-respect du CER peut entraîner le remboursement intégral. L'appréciation par le préfet est large et peut concerner des actions ou propos de salariés, d'élus ou d'adhérents tenus au nom de l'association. Plusieurs recours ont été engagés devant le Conseil d'État sur l'application du dispositif (Conseil d'État, 12 juillet 2023 n° 461962 : validation partielle). Il est recommandé de porter le CER à la connaissance du CA et de l'AG pour traçabilité.",
                "sources": [
                    "Loi n° 2021-1109 du 24 août 2021",
                    "Décret n° 2021-1947 du 31 décembre 2021",
                    "Art. 10-1 loi n° 2000-321 du 12 avril 2000",
                    "Conseil d'État, 12 juillet 2023 n° 461962",
                ],
                "liens": [
                    {"titre": "associations.gouv.fr — CER", "url": ASSOS_GOUV + "le-contrat-d-engagement-republicain.html"},
                    {"titre": "Décret 2021-1947 — Légifrance", "url": "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000044806609"},
                    {"titre": "Loi 2021-1109 — Légifrance", "url": "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000043964778"},
                ],
            },
            "fiches_pratiques": [],
        },
    ],
    "instances": [
        {
            "id": "gv-09",
            "question_type": "Quel est le rôle respectif de l'assemblée générale, du conseil d'administration et du bureau ?",
            "mots_cles": [
                "assemblée générale", "conseil d'administration", "bureau",
                "statuts", "organes", "loi 1901", "délibération",
                "quorum", "majorité", "procuration", "visioconférence",
            ],
            "reponse": {
                "synthese": "La loi du 1er juillet 1901 laisse aux associations une grande liberté pour s'organiser : elle n'impose PAS de structure particulière (CA, bureau, AG). Toutefois, la pratique et la plupart des statuts prévoient trois organes : (1) l'Assemblée Générale (AG), souveraine, qui rassemble tous les membres et prend les décisions stratégiques ; (2) le Conseil d'Administration (CA), élu par l'AG, qui administre l'association entre deux AG ; (3) le Bureau, émanation du CA, qui assure la gestion courante et représente l'association vis-à-vis des tiers.",
                "fondement_legal": "Loi du 1er juillet 1901 (aucune disposition contraignante sur les organes). Article 5 de la loi 1901 (déclaration des changements de dirigeants au RNA). Les règles précises sont celles fixées par les STATUTS de l'association, lesquels ont force de loi entre les membres (Cass. civ. 1, 15 avril 2015 n° 14-12.531). À défaut de précision statutaire, les règles générales du mandat s'appliquent (art. 1984 et s. du Code civil).",
                "fondement_ccn": "Sans objet. La gouvernance est statutaire. La CCN ALISFA concerne uniquement les relations employeur/salariés.",
                "application": "AG : délibère sur l'approbation des comptes, la décharge des administrateurs, l'élection des administrateurs, les modifications statutaires, la dissolution, les orientations stratégiques. CA : met en œuvre la politique définie par l'AG, arrête le budget et les comptes avant présentation à l'AG, embauche et licencie le directeur salarié, gère l'association au quotidien. Bureau : exécute les décisions du CA, gère les affaires courantes, représente l'association (signatures bancaires, contrats). Depuis les ordonnances du 25 mars 2020 et la loi ASAP du 7 décembre 2020, les AG et CA peuvent se tenir à distance (visioconférence ou audioconférence) même sans mention statutaire, sous conditions.",
                "vigilance": "Respecter scrupuleusement les statuts : un acte pris en violation des règles statutaires (convocation irrégulière, absence de quorum, dépassement des pouvoirs) peut être annulé en justice. Les PV d'AG et de CA doivent être conservés de manière fiable (registre spécial recommandé). Toute modification statutaire doit être déclarée à la préfecture (RNA) dans les 3 mois (art. 5 loi 1901) ; à défaut, amende de 1 500 €. Les décisions importantes (achat immobilier, emprunt, embauche directeur) doivent être mentionnées explicitement dans les statuts ou déléguées par écrit.",
                "sources": [
                    "Loi du 1er juillet 1901",
                    "Cass. civ. 1, 15 avril 2015 n° 14-12.531",
                    "Ordonnance n° 2020-321 du 25 mars 2020",
                    "Loi n° 2020-1525 du 7 décembre 2020 (ASAP)",
                    "Guide HCVA — fonctionnement statutaire",
                ],
                "liens": [
                    {"titre": "associations.gouv.fr — statuts et fonctionnement", "url": ASSOS_GOUV + "creer-votre-association.html"},
                    {"titre": "Loi 1901 — Légifrance", "url": LEGIFRANCE_1901},
                    {"titre": "Guide de l'association — associations.gouv.fr", "url": ASSOS_GOUV},
                ],
            },
            "fiches_pratiques": [],
        },
    ],
    "benevolat": [
        {
            "id": "gv-10",
            "question_type": "Quels sont les droits et protections des bénévoles (indemnités, formation, compte d'engagement citoyen) ?",
            "mots_cles": [
                "bénévole", "indemnisation frais", "barème kilométrique",
                "CEC", "Compte Engagement Citoyen", "formation bénévole",
                "FDVA", "abandon de frais", "réduction impôt",
                "66%", "reçu fiscal",
            ],
            "reponse": {
                "synthese": "Le bénévole n'est pas salarié : il n'a pas de contrat de travail, pas de rémunération, pas de lien de subordination. Il bénéficie cependant de droits spécifiques : remboursement des frais engagés (ou abandon de frais ouvrant droit à une réduction d'impôt), formation via le FDVA (Fonds pour le Développement de la Vie Associative), droits inscrits sur le Compte d'Engagement Citoyen (CEC) permettant d'acquérir des heures de formation mobilisables sur le CPF, et protection par l'assurance de l'association.",
                "fondement_legal": "Absence de texte unique : le bénévolat est défini négativement (pas de contrat de travail). Article 200 du Code général des impôts (CGI) : réduction d'impôt de 66 % pour abandon de frais au bénéfice d'une association d'intérêt général. Article L5151-9 et s. du Code du travail : Compte d'Engagement Citoyen. Article L6323-41-1 : mobilisation du CEC via le CPF. Loi n° 2017-86 du 27 janvier 2017 (égalité et citoyenneté) — création du CEC. Décret n° 2018-1080 du 4 décembre 2018 (modalités FDVA).",
                "fondement_ccn": "Sans objet. La CCN ne s'applique pas aux bénévoles.",
                "application": "Remboursement des frais : barème kilométrique bénévole publié chaque année par l'administration fiscale (actualisé au JO). Abandon de frais : le bénévole renonce expressément par écrit à son remboursement, ce qui lui ouvre droit à une réduction d'impôt de 66 % du montant (plafonnée à 20 % du revenu imposable) sur présentation d'un reçu fiscal Cerfa 11580. CEC : accès ouvert aux bénévoles ayant exercé au moins 200 heures au cours de l'année dans une association éligible, dont 100 heures minimum dans la même association (L5151-9 C. trav.). 240 € par année d'engagement, dans la limite de 720 €.",
                "vigilance": "Distinguer bénévolat et volontariat : le volontaire (service civique, corps européen de solidarité) a un statut protégé avec indemnité. Un bénévole requalifié en salarié par les juges (critères de subordination et de rémunération déguisée) expose l'association à un rappel de cotisations URSSAF et à une condamnation prud'homale. L'association doit vérifier que son assurance RC couvre bien les bénévoles pour les dommages qu'ils pourraient causer ou subir dans l'exercice de leur mission.",
                "sources": [
                    "Art. 200 CGI",
                    "Art. L5151-9 et s. C. trav.",
                    "Loi n° 2017-86 du 27 janvier 2017",
                    "Décret n° 2018-1080 du 4 décembre 2018 (FDVA)",
                    "Barème kilométrique bénévole (BOI-IR-RICI-250)",
                ],
                "liens": [
                    {"titre": "associations.gouv.fr — bénévolat", "url": ASSOS_GOUV + "les-outils-du-benevolat.html"},
                    {"titre": "CEC — mon compte bénévolat", "url": "https://www.service-public.fr/particuliers/vosdroits/F34030"},
                    {"titre": "FDVA — associations.gouv.fr", "url": ASSOS_GOUV + "le-fdva.html"},
                    {"titre": "BOI-IR-RICI-250 — barème bénévole", "url": "https://bofip.impots.gouv.fr/"},
                ],
            },
            "fiches_pratiques": [],
        },
    ],
    "patronat_associatif": [
        {
            "id": "gv-11",
            "question_type": "L'association est-elle assujettie aux impôts commerciaux et au RGPD ?",
            "mots_cles": [
                "association impôt", "IS", "TVA", "CET",
                "lucrativité", "règle 4P", "sectorisation", "rescrit fiscal",
                "RGPD", "données personnelles", "DPO", "CNIL",
                "traitement", "BOI-IS-CHAMP",
            ],
            "reponse": {
                "synthese": "Une association est en principe exonérée des trois impôts commerciaux (IS, TVA, CET) si sa gestion est désintéressée et ses activités non lucratives. L'administration fiscale apprécie la lucrativité via la « règle des 4 P » (Produit, Public, Prix, Publicité). Si l'association exerce à titre accessoire une activité lucrative, elle peut sectoriser ou filialiser. Par ailleurs, dès qu'elle traite des données personnelles (adhérents, donateurs, salariés, bénéficiaires), l'association est soumise au RGPD.",
                "fondement_legal": "Article 206-1 bis du Code général des impôts (assujettissement à l'IS). Instruction fiscale BOI-IS-CHAMP-10-50-10-20 (règle des 4 P). Article 261-7 du CGI (exonération TVA des services rendus aux membres). Franchise commerciale accessoire : 78 596 € pour 2024 (actualisation annuelle). Règlement (UE) 2016/679 du 27 avril 2016 (RGPD). Loi n° 78-17 du 6 janvier 1978 modifiée (Informatique et Libertés). Article 30 RGPD : registre des activités de traitement obligatoire dès le premier traitement.",
                "fondement_ccn": "Sans objet. La CCN ALISFA ne traite pas de fiscalité ni de protection des données côté association.",
                "application": "FISCAL — Démarche recommandée : (1) vérifier la gestion désintéressée (dirigeants bénévoles, non-distribution des excédents), (2) analyser la règle des 4 P (Produit : produit/service utile non concurrentiel ; Public : bénéficiaires justifiant une mission sociale ; Prix : tarifs inférieurs au marché ou modulés ; Publicité : communication non commerciale), (3) en cas de doute, adresser un rescrit fiscal à la DGFiP (art. L80 B CGI). RGPD — Démarche : (1) tenir un registre des traitements, (2) informer les personnes concernées, (3) recueillir les consentements valides, (4) sécuriser les données, (5) désigner un DPO si nécessaire, (6) gérer les droits d'accès, rectification, effacement, portabilité.",
                "vigilance": "Si l'activité lucrative accessoire dépasse 78 596 € HT (seuil 2024 actualisé chaque année), l'association perd l'exonération globale. Elle doit alors sectoriser (fiscalisation uniquement du secteur lucratif) ou tout fiscaliser. Côté RGPD, les sanctions CNIL vont jusqu'à 20 M€ ou 4 % du CA annuel. Les associations ALISFA manipulent fréquemment des données sensibles (enfance, santé, situation sociale) qui relèvent de l'article 9 RGPD et imposent des garanties renforcées (consentement explicite, DPIA, habilitations strictes).",
                "sources": [
                    "Art. 206-1 bis et 261-7 CGI",
                    "BOI-IS-CHAMP-10-50-10-20",
                    "Règlement (UE) 2016/679 (RGPD)",
                    "Loi n° 78-17 du 6 janvier 1978 modifiée",
                    "CNIL — guide associations",
                ],
                "liens": [
                    {"titre": "associations.gouv.fr — fiscalité", "url": ASSOS_GOUV + "la-fiscalite-des-associations.html"},
                    {"titre": "CNIL — RGPD associations", "url": "https://www.cnil.fr/fr/associations-les-bonnes-pratiques-du-rgpd"},
                    {"titre": "BOFiP — régime fiscal des associations", "url": "https://bofip.impots.gouv.fr/bofip/1174-PGP"},
                    {"titre": "CGI — art. 206", "url": "https://www.legifrance.gouv.fr/codes/texte_lc/LEGITEXT000006069577/"},
                ],
            },
            "fiches_pratiques": [],
        },
    ],
    "doctrine_recherche": [
        {
            "id": "gv-12",
            "question_type": "Quels sont les chiffres clés du paysage associatif français et leurs sources ?",
            "mots_cles": [
                "chiffres associations", "1,5 million associations",
                "CNRS Tchernonog", "INJEP", "paysage associatif",
                "emploi associatif", "bénévoles", "budget",
                "recherches vie associative", "HCVA",
            ],
            "reponse": {
                "synthese": "Le paysage associatif français compte environ 1,5 million d'associations actives, 20 millions de bénévoles (dont environ 13 millions réguliers), 1,8 million de salariés (dans 155 000 associations employeuses) et un budget cumulé d'environ 113 milliards d'euros, soit près de 3,3 % du PIB. Ces chiffres proviennent principalement de trois sources : l'enquête CNRS « Le paysage associatif français » de Viviane Tchernonog (référence académique), les publications de l'INJEP (Institut national de la jeunesse et de l'éducation populaire), et le panorama annuel Recherches & Solidarités.",
                "fondement_legal": "Ces statistiques relèvent de l'observation et non de la réglementation. Elles alimentent toutefois plusieurs rapports officiels : rapports du Haut Conseil à la Vie Associative (HCVA), avis du Conseil économique, social et environnemental (CESE), rapports parlementaires. Loi n° 2014-856 du 31 juillet 2014 (loi ESS) : reconnaissance officielle de l'économie sociale et solidaire dans laquelle les associations représentent environ 80 % des emplois.",
                "fondement_ccn": "Sans objet. La CPNEF ALISFA mène son propre travail d'observatoire pour la branche (cartographie des métiers, études prospectives) qui s'appuie sur ces sources nationales.",
                "application": "Pour documenter un dossier, utiliser : (1) pour les statistiques générales, l'enquête Tchernonog (CNRS, dernières éditions 2019 et 2024) et l'INJEP ; (2) pour l'emploi associatif, Recherches & Solidarités (paysage annuel des associations employeuses) et les données ACOSS-URSSAF ; (3) pour la vie associative locale, les observatoires régionaux (CRVA) ; (4) pour les dons et le mécénat, France Générosités et le Baromètre de la générosité. Toujours citer la source et l'année — le paysage évolue vite.",
                "vigilance": "Attention à la confusion entre nombre d'associations DÉCLARÉES (cumul historique au RNA, ~3 millions) et associations ACTIVES (estimation ~1,5 million). Les chiffres sur l'emploi associatif peuvent varier selon la méthode : l'ACOSS comptabilise les associations ayant au moins un salarié déclaré sur l'année, tandis que Recherches & Solidarités affine avec d'autres paramètres. Les données sur le bénévolat reposent sur des enquêtes déclaratives (IFOP, France Bénévolat) avec une marge d'incertitude.",
                "sources": [
                    "Tchernonog V., « Le paysage associatif français », CNRS/Dalloz-Juris associations (éd. 2019 et 2024)",
                    "INJEP — publications sur la vie associative",
                    "Recherches & Solidarités — panorama annuel des associations",
                    "Loi n° 2014-856 du 31 juillet 2014 (ESS)",
                    "HCVA — rapports biennaux",
                ],
                "liens": [
                    {"titre": "INJEP — vie associative", "url": "https://injep.fr/thematiques/vie-associative/"},
                    {"titre": "Recherches & Solidarités", "url": "https://recherches-solidarites.org/"},
                    {"titre": "HCVA — portail", "url": HCVA},
                    {"titre": "Le Mouvement associatif", "url": MVT_ASSO},
                    {"titre": "associations.gouv.fr — chiffres clés", "url": ASSOS_GOUV},
                ],
            },
            "fiches_pratiques": [],
        },
    ],
}


def main() -> int:
    data = json.loads(SRC.read_text(encoding="utf-8"))
    shutil.copy(SRC, BAK)

    themes = {t["id"]: t for t in data["themes"]}
    added = 0
    for theme_id, articles in NEW_ARTICLES.items():
        theme = themes.get(theme_id)
        if not theme:
            print(f"  ⚠ thème inconnu : {theme_id}")
            continue
        existing = {a["id"] for a in theme["articles"]}
        for art in articles:
            if art["id"] in existing:
                print(f"  ⏭  déjà présent : {art['id']}")
                continue
            theme["articles"].append(art)
            added += 1
            print(f"  ✅ {theme_id} :: {art['id']} — {art['question_type'][:70]}")

    data.setdefault("metadata", {})["date_consolidation"] = "2026-04-15"
    data["metadata"].setdefault("enrichissements", []).append(
        {
            "date": "2026-04-15",
            "source": "Loi 1901, associations.gouv.fr, HCVA, CNRS Tchernonog, INJEP, CNIL, BOFiP",
            "ajouts": [a["id"] for arts in NEW_ARTICLES.values() for a in arts],
            "note": "Responsabilité dirigeants bénévoles, CER, organes statutaires, droits bénévoles, fiscalité + RGPD, chiffres clés vie associative.",
        }
    )

    SRC.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{added} article(s) ajouté(s). Sauvegarde : {BAK}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
