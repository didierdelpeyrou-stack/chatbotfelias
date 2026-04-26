"""Endpoints fiches métiers CPNEF — Sprint 4.6 F5.

Liste des 25 fiches métiers ALISFA officielles + documents annexes,
servies en lecture seule.

  GET /api/fiches-metiers          → familles + fiches + docs annexes
  GET /api/fiches-metiers/familles → familles uniquement
  GET /api/fiches-metiers/all      → 25 fiches à plat
"""
from __future__ import annotations

from fastapi import APIRouter

from app.llm.fiches_metiers import (
    list_docs_annexes,
    list_familles,
    list_fiches,
)

router = APIRouter(tags=["fiches-metiers"], prefix="/api/fiches-metiers")


@router.get("", summary="Fiches métiers + familles + documents annexes")
async def get_fiches_metiers() -> dict:
    """Réponse complète pour l'UI : familles avec fiches + docs annexes."""
    return {
        "familles": list_familles(),
        "docs_annexes": list_docs_annexes(),
        "total": len(list_fiches()),
    }


@router.get("/familles", summary="Familles métiers uniquement")
async def get_familles() -> dict:
    return {"familles": list_familles()}


@router.get("/all", summary="Toutes les fiches à plat")
async def get_all_fiches() -> dict:
    return {"fiches": list_fiches()}
