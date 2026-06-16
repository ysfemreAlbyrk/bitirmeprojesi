"""JWT authentication dependency using Supabase JWT secret"""
import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.utils.logger import get_logger
from config import settings

logger = get_logger("vibetale")

_bearer_scheme = HTTPBearer()


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Security(_bearer_scheme),
) -> str:
    """Validate Supabase JWT and return the user's UUID (sub claim)."""
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256", "ES256"],
            options={"verify_aud": False},
        )
    except jwt.ExpiredSignatureError:
        logger.warning("Süresi dolmuş JWT ile istek atıldı")
        raise HTTPException(status_code=401, detail="Oturum süresi dolmuş, lütfen tekrar giriş yapın")
    except jwt.InvalidTokenError:
        logger.warning("JWT hem HS256 hem ES256 ile doğrulanamadı")
        raise HTTPException(status_code=401, detail="Geçersiz kimlik bilgisi")

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token geçersiz: user_id bulunamadı")
    return user_id
