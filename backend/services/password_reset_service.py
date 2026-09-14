import hashlib
import secrets
from datetime import datetime, timedelta, timezone


RESET_TOKEN_EXPIRATION_MINUTES = 5


def generate_reset_token() -> str:
    return secrets.token_urlsafe(32)


def hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def get_reset_token_expiration() -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_EXPIRATION_MINUTES)


def verify_reset_token(token: str, token_hash: str,) -> bool:
    return hash_reset_token(token) == token_hash