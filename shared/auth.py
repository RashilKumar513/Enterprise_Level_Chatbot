import hashlib
import secrets

from shared.config import ADMIN_PASSWORD, ADMIN_USERNAME, setup_logging

logger = setup_logging(__name__)

_PBKDF2_ITERATIONS = 120_000


def hash_password(password: str, salt: str | None = None) -> str:
    """Return salt$hash string for storage."""
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        _PBKDF2_ITERATIONS,
    )
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, expected = stored_hash.split("$", 1)
    except ValueError:
        return False
    actual = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        _PBKDF2_ITERATIONS,
    ).hex()
    return secrets.compare_digest(actual, expected)


def verify_credentials(username: str, password: str) -> bool:
    """Verify username/password against the users table."""
    from shared.database import get_user_password_hash

    stored = get_user_password_hash(username)
    if not stored:
        return False
    return verify_password(password, stored)
