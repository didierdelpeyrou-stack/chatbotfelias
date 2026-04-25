"""LLM wrapper V2 — Anthropic SDK async + prompts par module + R11.

Trois fixes vs V1 (cf. _AUDIT_RAG_performance) :
  - R7  : prompts qui imposent verbatim + citations (anti-hallucination)
  - R11 : pas de paraphrase libre des articles RAG
  - Async natif → streaming SSE possible (Sprint 3.2)

Sprint 5+ : ajout du tool calling, du fallback en cas de panne API, etc.
"""
