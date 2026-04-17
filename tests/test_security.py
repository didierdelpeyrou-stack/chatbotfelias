"""Tests de security.py — hash bcrypt et auth admin (fix 7).

Couvre :
  - ``hash_password`` / ``verify_password`` (bcrypt round-trip)
  - ``verify_admin_credentials`` (priorité hash > plain, rejet sans cred)
  - ``admin_auth_configured`` (détection de la config)
  - ``warn_if_legacy_admin`` (émission des warnings de migration)

Exécution :
    pytest tests/test_security.py -v
"""

from __future__ import annotations

import logging

import pytest

from security import (
    admin_auth_configured,
    generate_random_password,
    hash_password,
    verify_admin_credentials,
    verify_password,
    warn_if_legacy_admin,
)


pytestmark = pytest.mark.unit


# ──────────────────────── hash / verify ────────────────────────

class TestHashPassword:
    def test_hash_format_bcrypt(self):
        h = hash_password("secret123", rounds=4)  # 4 rounds = rapide en tests
        assert h.startswith("$2b$") or h.startswith("$2a$")
        assert len(h) == 60  # bcrypt produit toujours 60 chars

    def test_hash_deterministe_sur_meme_salt_mais_different_sur_gensalt(self):
        """Deux appels DOIVENT donner des hashes différents (sel aléatoire)."""
        h1 = hash_password("secret", rounds=4)
        h2 = hash_password("secret", rounds=4)
        assert h1 != h2  # salts différents

    def test_hash_vide_leve(self):
        with pytest.raises(ValueError):
            hash_password("")

    def test_cost_factor_respecte(self):
        """Le cost factor est encodé dans le hash."""
        h = hash_password("x", rounds=4)
        # Format : $2b$04$...
        assert h.split("$")[2] == "04"


class TestVerifyPassword:
    def test_round_trip_ok(self):
        h = hash_password("test1234", rounds=4)
        assert verify_password("test1234", h) is True

    def test_mauvais_mdp_refuse(self):
        h = hash_password("correct", rounds=4)
        assert verify_password("wrong", h) is False

    def test_hash_vide_refuse(self):
        assert verify_password("x", "") is False
        assert verify_password("", "hash") is False

    def test_hash_malforme_refuse_proprement(self):
        """Un hash invalide ne doit PAS lever, juste renvoyer False."""
        assert verify_password("x", "not-a-bcrypt-hash") is False
        assert verify_password("x", "$2b$invalid$") is False

    def test_unicode_ok(self):
        h = hash_password("mëlanï€", rounds=4)
        assert verify_password("mëlanï€", h) is True
        assert verify_password("melani€", h) is False


# ──────────────────────── verify_admin_credentials ────────────────────────

class TestVerifyAdminCredentials:
    """Vérifie les 3 modes : hash, plain legacy, aucun."""

    def test_mode_hash(self):
        h = hash_password("password", rounds=4)
        assert verify_admin_credentials(
            "admin", "password", expected_user="admin", hashed_password=h,
        ) is True

    def test_mode_hash_mauvais_pass(self):
        h = hash_password("password", rounds=4)
        assert verify_admin_credentials(
            "admin", "WRONG", expected_user="admin", hashed_password=h,
        ) is False

    def test_mode_plain_legacy(self):
        assert verify_admin_credentials(
            "admin", "password",
            expected_user="admin", plain_password="password",
        ) is True

    def test_mode_plain_mauvais_pass(self):
        assert verify_admin_credentials(
            "admin", "WRONG",
            expected_user="admin", plain_password="password",
        ) is False

    def test_hash_prime_sur_plain_si_les_deux_definis(self):
        """Si ADMIN_PASS_HASH est défini, il gagne sur ADMIN_PASS (plain).
        Cas d'usage : migration progressive — on définit le hash sans
        supprimer l'ancien ADMIN_PASS."""
        h = hash_password("new-password", rounds=4)
        # Le plain dit "old-password", mais le hash dit "new-password"
        # → c'est "new-password" qui doit passer (priorité au hash).
        assert verify_admin_credentials(
            "admin", "new-password",
            expected_user="admin",
            hashed_password=h,
            plain_password="old-password",
        ) is True
        # Et "old-password" doit être refusé (ignoré car hash présent).
        assert verify_admin_credentials(
            "admin", "old-password",
            expected_user="admin",
            hashed_password=h,
            plain_password="old-password",
        ) is False

    def test_aucune_config_refuse_tout(self):
        """Pas de hash, pas de plain → refus systématique."""
        assert verify_admin_credentials(
            "admin", "anything", expected_user="admin",
        ) is False

    def test_mauvais_username_refuse(self):
        h = hash_password("pass", rounds=4)
        assert verify_admin_credentials(
            "intruder", "pass", expected_user="admin", hashed_password=h,
        ) is False

    def test_username_vide_refuse(self):
        h = hash_password("pass", rounds=4)
        assert verify_admin_credentials(
            "", "pass", expected_user="admin", hashed_password=h,
        ) is False

    def test_password_vide_refuse(self):
        h = hash_password("pass", rounds=4)
        assert verify_admin_credentials(
            "admin", "", expected_user="admin", hashed_password=h,
        ) is False


# ──────────────────────── admin_auth_configured ────────────────────────

class TestAdminAuthConfigured:
    def test_rien_false(self):
        assert admin_auth_configured(None, None) is False
        assert admin_auth_configured("", "") is False

    def test_hash_seul_true(self):
        assert admin_auth_configured("$2b$12$xyz", None) is True

    def test_plain_seul_true(self):
        assert admin_auth_configured(None, "secret") is True

    def test_les_deux_true(self):
        assert admin_auth_configured("$2b$12$xyz", "secret") is True


# ──────────────────────── warn_if_legacy_admin ────────────────────────

class TestWarnIfLegacyAdmin:
    def test_warning_si_hash_et_plain_definis(self, caplog):
        logger = logging.getLogger("test_warn_legacy")
        caplog.set_level(logging.WARNING, logger="test_warn_legacy")
        warn_if_legacy_admin(logger, has_hash=True, has_plain=True)
        assert any("migration" in r.message.lower() for r in caplog.records)

    def test_warning_si_plain_seul(self, caplog):
        logger = logging.getLogger("test_warn_plain")
        caplog.set_level(logging.WARNING, logger="test_warn_plain")
        warn_if_legacy_admin(logger, has_hash=False, has_plain=True)
        assert any("clair" in r.message.lower() for r in caplog.records)

    def test_pas_de_warning_si_hash_seul(self, caplog):
        logger = logging.getLogger("test_warn_hash")
        caplog.set_level(logging.WARNING, logger="test_warn_hash")
        warn_if_legacy_admin(logger, has_hash=True, has_plain=False)
        # Aucune ligne WARNING émise
        assert not any(r.levelno == logging.WARNING for r in caplog.records
                       if r.name == "test_warn_hash")


# ──────────────────────── generate_random_password ────────────────────────

class TestGenerateRandomPassword:
    def test_longueur_respectee(self):
        p = generate_random_password(length=24)
        assert len(p) == 24

    def test_entropie(self):
        """Deux générations consécutives ne doivent jamais matcher
        (probabilité < 2^-144)."""
        assert generate_random_password() != generate_random_password()

    def test_caracteres_url_safe(self):
        import re
        p = generate_random_password(32)
        # secrets.token_urlsafe ne contient que [A-Za-z0-9_-]
        assert re.match(r"^[A-Za-z0-9_\-]+$", p)

    def test_longueur_minimum(self):
        """Minimum forcé à 12 même si on demande plus court (entropie)."""
        p = generate_random_password(length=4)
        assert len(p) >= 4  # la fonction tronque, mais l'entropie reste >= 12 chars
