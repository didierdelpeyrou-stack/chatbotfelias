"""Module feedback — collecte 👍/👎 utilisateurs (Sprint 4.3).

Concept ML inline : RLHF (Reinforcement Learning from Human Feedback).
Les ratings utilisateurs forment un dataset de "preference data" :
chaque entrée (question, réponse, rating) sera plus tard exploitable pour :
  - identifier les modules/types de questions où le bot échoue (analyse),
  - constituer un reward model (T1+, hors scope du Sprint 4.3),
  - prioriser les chantiers d'enrichissement KB.

Pour l'instant on ne fait QUE collecter — pas de re-ranking en ligne.
"""
