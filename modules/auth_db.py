from __future__ import annotations
import hashlib
import os
from typing import Optional, Dict, Any, List

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend
import bcrypt
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

# ---------------------------------------------------------------------------
# MongoDB connection
# ---------------------------------------------------------------------------
MONGODB_URI = (
    "mongodb://moeezsalman246:1234567890@"
    "ac-5ctfzjl-shard-00-00.slr01tl.mongodb.net:27017,"
    "ac-5ctfzjl-shard-00-01.slr01tl.mongodb.net:27017,"
    "ac-5ctfzjl-shard-00-02.slr01tl.mongodb.net:27017/"
    "phantomBits?ssl=true&replicaSet=atlas-kgs04r-shard-0"
    "&authSource=admin&retryWrites=true&w=majority"
)

client = MongoClient(MONGODB_URI)
db = client["phantomBits"]
users_col = db["users"]

# Create unique index on gmail (run once)
users_col.create_index("gmail", unique=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def hash_value(value: str) -> str:
    """SHA-256 hash (used for userID and public key storage)."""
    return hashlib.sha256(value.encode()).hexdigest()


def generate_rsa_keypair() -> tuple[str, str]:
    """
    Generate RSA-2048 key pair.
    Returns (public_pem, private_pem) as UTF-8 strings.
    """
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()

    return public_pem, private_pem


def encrypt_with_public_key(plaintext: str, public_pem: str) -> bytes:
    """Encrypt a short string (the AES password) with recipient's public key."""
    public_key = serialization.load_pem_public_key(
        public_pem.encode(), backend=default_backend()
    )
    ciphertext = public_key.encrypt(
        plaintext.encode(),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return ciphertext


def decrypt_with_private_key(ciphertext: bytes, private_pem: str) -> str:
    """Decrypt with the user's private key. Raises ValueError on failure."""
    try:
        private_key = serialization.load_pem_private_key(
            private_pem.encode(), password=None, backend=default_backend()
        )
        plaintext = private_key.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        return plaintext.decode()
    except Exception as exc:
        raise ValueError("Wrong private key or corrupted data") from exc


# ---------------------------------------------------------------------------
# User CRUD
# ---------------------------------------------------------------------------
def create_user(gmail: str, password: str, public_key: str) -> Dict[str, Any]:
    """
    Create a new user.
    - password is hashed with bcrypt
    - userID = SHA256(gmail)
    - public_key is also stored as SHA256 hash (as you requested)
    - the actual public_key PEM is also stored so we can use it later
    """
    user_id = hash_value(gmail)
    doc = {
        "userID": user_id,                     # hashed
        "gmail": gmail.lower().strip(),
        "password": hash_password(password),
        "public_key": public_key,              # full PEM (needed for encryption)
        "public_key_hash": hash_value(public_key),  # as you requested
    }
    try:
        users_col.insert_one(doc)
        return doc
    except DuplicateKeyError:
        raise ValueError("A user with this Gmail already exists.")


def authenticate(gmail: str, password: str) -> Optional[Dict[str, Any]]:
    user = users_col.find_one({"gmail": gmail.lower().strip()})
    if user and check_password(password, user["password"]):
        return user
    return None


def search_users_by_gmail(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Simple prefix / contains search on gmail."""
    if not query:
        return []
    regex = {"$regex": query, "$options": "i"}
    cursor = users_col.find(
        {"gmail": regex},
        {"gmail": 1, "public_key": 1, "userID": 1, "_id": 0},
    ).limit(limit)
    return list(cursor)


def get_user_by_gmail(gmail: str) -> Optional[Dict[str, Any]]:
    return users_col.find_one(
        {"gmail": gmail.lower().strip()},
        {"gmail": 1, "public_key": 1, "userID": 1, "_id": 0},
    )