from jose import JWTError, jwt
from app.core.config import settings

def decode_access_token(token: str) -> dict:
    """Decode and verify a JWT access token. Validates signature with shared secret."""
    payload = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )
    if payload.get("type") != "access":
        raise JWTError("Token is not an access token")
    return payload
