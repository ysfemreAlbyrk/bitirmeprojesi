#!/usr/bin/env python3
"""
VibeTale — Supabase Key Generator
Generates JWT_SECRET, ANON_KEY, SERVICE_ROLE_KEY, and PG_META_CRYPTO_KEY
and optionally updates the .env file in place.

Uses Python standard library only — no pip installs required.

Usage:
    python generate_keys.py
"""
import base64
import hashlib
import hmac
import json
import re
import secrets
import time
from pathlib import Path


# ── JWT helpers (HS256, stdlib only) ─────────────────────────────────────────

def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _make_jwt(payload: dict, secret: str) -> str:
    header_b64 = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload_b64 = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    message = f"{header_b64}.{payload_b64}".encode()
    sig = hmac.new(secret.encode(), message, hashlib.sha256).digest()
    return f"{header_b64}.{payload_b64}.{_b64url(sig)}"


# ── Key generation ────────────────────────────────────────────────────────────

def generate_keys() -> dict:
    jwt_secret = secrets.token_hex(32)          # 64-char hex ≥ 32-char requirement
    pg_meta_key = secrets.token_hex(16)         # 32-char hex

    now = int(time.time())
    exp = now + 5 * 365 * 24 * 3600            # 5 years

    anon_key = _make_jwt(
        {"role": "anon", "iss": "supabase", "iat": now, "exp": exp},
        jwt_secret,
    )
    service_key = _make_jwt(
        {"role": "service_role", "iss": "supabase", "iat": now, "exp": exp},
        jwt_secret,
    )

    return {
        "JWT_SECRET": jwt_secret,
        "ANON_KEY": anon_key,
        "SERVICE_ROLE_KEY": service_key,
        "PG_META_CRYPTO_KEY": pg_meta_key,
    }


# ── .env patching ─────────────────────────────────────────────────────────────

def patch_env(keys: dict, env_path: Path) -> None:
    content = env_path.read_text(encoding="utf-8")

    replacements = {
        "JWT_SECRET": keys["JWT_SECRET"],
        "ANON_KEY": keys["ANON_KEY"],
        "SERVICE_ROLE_KEY": keys["SERVICE_ROLE_KEY"],
        "SUPABASE_KEY": keys["ANON_KEY"],
        "SUPABASE_SERVICE_KEY": keys["SERVICE_ROLE_KEY"],
        "PG_META_CRYPTO_KEY": keys["PG_META_CRYPTO_KEY"],
    }

    for var, value in replacements.items():
        content = re.sub(
            rf"^{var}=.*$",
            f"{var}={value}",
            content,
            flags=re.MULTILINE,
        )

    env_path.write_text(content, encoding="utf-8")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    sep = "=" * 62
    print(f"\n{sep}")
    print("  VibeTale — Supabase Key Generator")
    print(sep)

    keys = generate_keys()

    print("\nGenerated keys:\n")
    for k, v in keys.items():
        print(f"{k}={v}\n")
    print(sep)

    env_path = Path(".env")
    if not env_path.exists():
        print("\n⚠  .env not found — copy the values above manually.")
        return

    answer = input("\nUpdate .env automatically? (y/N): ").strip().lower()
    if answer != "y":
        print("No changes made. Copy the values above into your .env file.")
        return

    patch_env(keys, env_path)
    print("\n✓  .env updated successfully!")
    print("   Next: set POSTGRES_PASSWORD and DASHBOARD_PASSWORD in .env")
    print("   Then: docker compose pull && docker compose up -d\n")


if __name__ == "__main__":
    main()
