import secrets
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Generate a secure Argon2 password hash."""
    return password_hash.hash(password)


def verify_password(password: str, stored_password: str) -> bool:
    """Verify both Argon2 hashes and legacy plaintext passwords."""

    if stored_password.startswith("$argon2"):
        return password_hash.verify(password, stored_password)

    # Legacy account: compare plaintext safely.
    return secrets.compare_digest(password, stored_password)


def is_hashed_password(stored_password: str) -> bool:
    return stored_password.startswith("$argon2")