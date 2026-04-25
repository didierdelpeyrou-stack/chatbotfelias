"""Helpers de validation des KB — appelés au boot par le KBStore (Sprint 3.1).

Usage typique :
    from app.kb.validators import validate_kb_file
    kb = validate_kb_file(Path("data/base_juridique.json"))
    # → ValidationError si la KB est mal formée. App refuse de démarrer.

Conception : on remonte des messages d'erreur **utilisables**, pas des
stack traces Pydantic illisibles. Format : `<base>:<theme>:<article> – <champ>: <raison>`.
"""
from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from app.kb.schema import KnowledgeBase


class KBValidationError(Exception):
    """Erreur de validation enrichie : nom du fichier + détails Pydantic."""

    def __init__(self, source: str, errors: list[dict]):
        self.source = source
        self.errors = errors
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        lines = [f"KB invalide ({self.source}) — {len(self.errors)} erreur(s) :"]
        for err in self.errors[:10]:  # Limite à 10 pour lisibilité
            loc = ".".join(str(p) for p in err.get("loc", []))
            msg = err.get("msg", "(no message)")
            lines.append(f"  - {loc} : {msg}")
        if len(self.errors) > 10:
            lines.append(f"  ... et {len(self.errors) - 10} autres.")
        return "\n".join(lines)


def validate_kb_dict(data: dict, *, source: str = "<dict>") -> KnowledgeBase:
    """Valide un dict (chargé depuis JSON) contre le schéma `KnowledgeBase`.

    Args:
      data: dict typiquement issu de `json.load(file)`.
      source: nom de fichier ou identifiant — apparaît dans les messages d'erreur.

    Returns:
      Instance `KnowledgeBase` typée et validée.

    Raises:
      KBValidationError: si le schéma n'est pas respecté.
    """
    try:
        return KnowledgeBase.model_validate(data)
    except ValidationError as e:
        raise KBValidationError(source, e.errors()) from e


def validate_kb_file(path: Path | str) -> KnowledgeBase:
    """Charge un fichier JSON et le valide.

    Args:
      path: chemin vers le fichier KB (ex. `data/base_juridique.json`).

    Returns:
      Instance `KnowledgeBase` typée et validée.

    Raises:
      FileNotFoundError: si le fichier n'existe pas.
      KBValidationError: si le contenu n'est pas conforme au schéma.
      json.JSONDecodeError: si le fichier n'est pas du JSON valide.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"KB introuvable : {p}")
    with p.open(encoding="utf-8") as f:
        data = json.load(f)
    return validate_kb_dict(data, source=str(p))
