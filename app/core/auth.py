"""JWT authentication dependency using Supabase JWT secret"""
import base64
import json
from pathlib import Path

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.utils.logger import get_logger
from config import settings

logger = get_logger("vibetale")

_bearer_scheme = HTTPBearer()


def _jwk_to_pem(jwk: dict) -> bytes:
    """Convert ES256 JWK public key to PEM format."""
    def b64url_to_int(val: str) -> int:
        padding = 4 - len(val) % 4
        if padding != 4:
            val += '=' * padding
        return int.from_bytes(base64.urlsafe_b64decode(val), 'big')

    x = b64url_to_int(jwk['x'])
    y = b64url_to_int(jwk['y'])

    public_numbers = ec.EllipticCurvePublicNumbers(x, y, ec.SECP256R1())
    public_key = public_numbers.public_key()

    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )


def _load_jwt_key():
    """Load JWT verification key and algorithm from signing_keys.json or fallback to settings."""
    keys_path = Path(__file__).parent.parent.parent / "supabase" / "signing_keys.json"
    print(f"[AUTH DEBUG] Looking for signing keys at: {keys_path} (exists={keys_path.exists()})")
    logger.info(f"Looking for signing keys at: {keys_path} (exists={keys_path.exists()})")
    if keys_path.exists():
        try:
            with open(keys_path, encoding='utf-8') as f:
                keys = json.load(f)
            for key in keys:
                if key.get("alg") == "ES256" and key.get("use") == "sig":
                    pem = _jwk_to_pem(key)
                    logger.info(f"Loaded ES256 signing key (kid: {key.get('kid')}) from {keys_path}")
                    return pem, "ES256"
        except Exception as exc:
            logger.warning(f"Failed to load signing_keys.json: {exc}")

    logger.info("Using HS256 JWT secret from settings")
    return settings.supabase_jwt_secret, "HS256"


# Module-level cache: load key once at import time
_jwt_secret, _jwt_algorithm = _load_jwt_key()


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Security(_bearer_scheme),
) -> str:
    """Validate Supabase JWT and return the user's UUID (sub claim)."""
    token = credentials.credentials
    secret = _jwt_secret
    algorithm = _jwt_algorithm

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[algorithm],
            options={"verify_aud": False},
        )
    except jwt.ExpiredSignatureError:
        logger.warning("Süresi dolmuş JWT ile istek atıldı")
        raise HTTPException(status_code=401, detail="Oturum süresi dolmuş, lütfen tekrar giriş yapın")
    except jwt.InvalidTokenError:
        logger.warning("Geçersiz JWT")
        if isinstance(secret, str) and secret.startswith('super-secret'):
            raise HTTPException(
                status_code=500,
                detail="Sunucu yapılandırma hatası: .env'deki SUPABASE_JWT_SECRET gerçek değil. Supabase Dashboard > Settings > API > JWT Secret değerini .env'ye yapıştırın."
            )
        raise HTTPException(status_code=401, detail="Geçersiz kimlik bilgisi")

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token geçersiz: user_id bulunamadı")
    return user_id
