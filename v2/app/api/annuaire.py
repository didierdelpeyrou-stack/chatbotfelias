"""Endpoints annuaire d'orientation — Sprint 4.6 F6.

Expose 4 endpoints en lecture seule :

  GET /api/annuaire/orientations         → liste des natures de problème (cards UI)
  GET /api/annuaire/orientation/<id>     → orientation + acteurs résolus
  GET /api/annuaire/regions              → fédérations FCSF/ACEPP + référent ELISFA par région
  GET /api/annuaire/acteurs              → liste de tous les acteurs (debug / admin)
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.llm.annuaire import (
    expand_orientation,
    list_acteurs,
    list_orientations,
    list_regions,
)

router = APIRouter(tags=["annuaire"], prefix="/api/annuaire")


@router.get("/orientations", summary="Liste des natures de problème")
async def get_orientations() -> dict:
    """Retourne les orientations sans la liste détaillée des acteurs (cards UI)."""
    return {
        "orientations": [
            {
                "id": o["id"],
                "label": o["label"],
                "icon": o["icon"],
                "description": o["description"],
                "n_acteurs": len(o["acteurs"]),
            }
            for o in list_orientations()
        ],
    }


@router.get("/orientation/{orientation_id}", summary="Acteurs pour une orientation")
async def get_orientation_detail(orientation_id: str) -> dict:
    """Retourne l'orientation enrichie avec les fiches acteurs complètes."""
    expanded = expand_orientation(orientation_id)
    if expanded is None:
        raise HTTPException(404, f"Orientation inconnue : {orientation_id}")
    return expanded


@router.get("/regions", summary="Fédérations par région ELISFA")
async def get_regions() -> dict:
    """Retourne les 14 régions ELISFA avec référent + fédérations FCSF/ACEPP."""
    return {"regions": list_regions()}


@router.get("/acteurs", summary="Tous les acteurs (annuaire complet)")
async def get_acteurs() -> dict:
    """Liste exhaustive des acteurs (utile pour vue 'Tous les acteurs')."""
    return {"acteurs": list_acteurs()}
