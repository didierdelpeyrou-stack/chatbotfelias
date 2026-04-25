"""Module RAG V2 — TF-IDF + seuil hors_corpus + score normalisé.

Trois fixes vs V1 (cf. _AUDIT_RAG_performance_2026-04-21.md) :
  - R1 : seuil hors_corpus (threshold de décision)
  - R2 : score normalisé (comparable inter-modules)
  - R4 : filtre substring (tokens < 3 chars ignorés)

Pas encore couvert (Sprint 5+) :
  - R6 : rerank sémantique (E5-small embedding)
"""
