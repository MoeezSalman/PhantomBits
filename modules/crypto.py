"""
AES-256-GCM encryption / decryption with Scrypt key derivation.
"""

from __future__ import annotations
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt


# Fixed parameters (do not change without updating both sides)
SALT_SIZE = 16
NONCE_SIZE = 12
KEY_SIZE = 32          # 256-bit
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1


def _derive_key(password: str, salt: bytes) -> bytes:
    """Derive a 256-bit key from the password using Scrypt."""
    kdf = Scrypt(
        salt=salt,
        length=KEY_SIZE,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
    )
    return kdf.derive(password.encode("utf-8"))


def encrypt_message(message: str, password: str) -> bytes:
    """
    Encrypt a plaintext message.

    Returns a single bytes object:
        salt (16) || nonce (12) || ciphertext+tag
    """
    if not message:
        raise ValueError("Message cannot be empty")
    if not password:
        raise ValueError("Password cannot be empty")

    salt = os.urandom(SALT_SIZE)
    key = _derive_key(password, salt)
    nonce = os.urandom(NONCE_SIZE)

    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, message.encode("utf-8"), None)

    return salt + nonce + ciphertext


def decrypt_message(encrypted: bytes, password: str) -> str:
    """
    Decrypt data produced by encrypt_message.

    Raises ValueError on wrong password or tampered data.
    """
    if len(encrypted) < SALT_SIZE + NONCE_SIZE + 16:
        raise ValueError("Encrypted data is too short / corrupted")

    salt = encrypted[:SALT_SIZE]
    nonce = encrypted[SALT_SIZE : SALT_SIZE + NONCE_SIZE]
    ciphertext = encrypted[SALT_SIZE + NONCE_SIZE :]

    key = _derive_key(password, salt)
    aesgcm = AESGCM(key)

    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")
    except Exception as exc:
        raise ValueError("Decryption failed – wrong password or data was modified") from exc