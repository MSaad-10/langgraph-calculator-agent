import hashlib
import secrets
from datetime import datetime, timedelta, timezone


OTP_EXPIRATION_MINUTES = 5

def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"    # generates a 6 digit random otp from 000000 -> 999999

def hash_otp(otp: str) -> str:
    return hashlib.sha256(otp.encode("utf-8")).hexdigest()

def verify_otp(otp: str, otp_hash: str) -> bool:
    return hash_otp(otp) == otp_hash

def get_otp_expiration() -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRATION_MINUTES)