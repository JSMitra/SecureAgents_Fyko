"""
crypto_utils.py — RSA-2048 key-pair generation + encrypt/decrypt helpers.

Each agent generates a key pair on startup:
  - Stores its PEM public key in PostgreSQL `agent_keys`
  - Fetches the peer's public key from the same table
  - Encrypts sensitive payloads (model ULID + AES key material) with the
    recipient's RSA public key before sending via A2A
"""

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend


def generate_rsa_keypair():
    """
    Generate an RSA-2048 key pair.

    Returns
    -------
    private_key : RSAPrivateKey
    public_key  : RSAPublicKey
    """
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )
    return private_key, private_key.public_key()


def private_key_to_pem(private_key) -> str:
    """Serialize RSA private key to PEM string (no password)."""
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()


def public_key_to_pem(public_key) -> str:
    """Serialize RSA public key to PEM string."""
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()


def load_public_key_from_pem(pem: str):
    """Load an RSA public key from a PEM string."""
    return serialization.load_pem_public_key(pem.encode(), backend=default_backend())


def load_private_key_from_pem(pem: str):
    """Load an RSA private key from a PEM string."""
    return serialization.load_pem_private_key(
        pem.encode(), password=None, backend=default_backend()
    )


def rsa_encrypt(plaintext: str, public_key) -> bytes:
    """
    Encrypt *plaintext* string with *public_key* using OAEP/SHA-256.

    Returns raw ciphertext bytes.
    """
    return public_key.encrypt(
        plaintext.encode(),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )


def rsa_decrypt(ciphertext: bytes, private_key) -> str:
    """
    Decrypt *ciphertext* bytes with *private_key* using OAEP/SHA-256.

    Returns the original plaintext string.
    """
    return private_key.decrypt(
        ciphertext,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    ).decode()
