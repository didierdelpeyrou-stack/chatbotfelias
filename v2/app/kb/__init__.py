"""KB V2 — schémas Pydantic + validation au boot.

Trois niveaux de rigueur :

  - schema.py     : modèles **permissifs** acceptant les KB V1 actuelles
                    (niveau theme optional, reponse field free-form).
  - validators.py : helpers `validate_kb_dict()` / `validate_kb_file()`.
  - Sprint 5.1     : migration vers schéma **strict** (niveau article,
                    escalade, revision obligatoires) via `migrate_kb_v1_v2.py`.

Pourquoi commencer permissif :
  - les 4 KB V1 (juridique/formation/rh/gouvernance) ont des champs hétérogènes
  - on veut pouvoir valider AU BOOT pour détecter une corruption JSON
  - on resserrera progressivement quand les enrichissements seront en place
"""
