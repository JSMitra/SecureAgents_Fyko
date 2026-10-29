"""
fyko_ann.py — ANN-based AES key generation + AES encrypt/decrypt helpers.

Implements the FYKO thesis key-derivation pipeline exactly as specified:
  1. MD5 the random_string and utc_time → binary strings (128-bit each)
  2. Interleave → 256-bit input vector
  3. Feed through Keras ANN
  4. Threshold output at mean → 256-bit key string → hex
"""

import hashlib
import base64
import numpy as np
import tensorflow as tf
from Crypto.Cipher import AES


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_binary_md5(s: str) -> str:
    """Return 128-character binary string for MD5 of *s*."""
    return bin(int(hashlib.md5(s.encode()).hexdigest(), 16))[2:].zfill(128)


def _interleave(a, b):
    """Interleave two equal-length iterables element-by-element."""
    return [x for pair in zip(a, b) for x in pair]


def _join_binary(b1, b2):
    """Interleave two binary-character lists/strings and return int list."""
    combined = _interleave(b1, b2)
    return [1 if c == "1" else 0 for c in combined]


def _bin_to_hex(binary_string: str) -> str:
    """Convert a binary string to a lowercase hex string."""
    pad = len(binary_string) % 4
    binary_string = "0" * pad + binary_string
    return "".join(
        hex(int(binary_string[i * 4 : i * 4 + 4], 2))[2:]
        for i in range(len(binary_string) // 4)
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_aes_key(model, random_string: str, utc_time: int) -> str:
    """
    Derive a 256-bit AES key (as a 64-char hex string) from a Keras ANN
    model, a random string, and a UTC timestamp integer.

    Parameters
    ----------
    model         : Loaded Keras/TF model (from pickle or tf.keras.models.load_model)
    random_string : Arbitrary string (stored alongside key material so it can be
                    reproduced by the reviewer)
    utc_time      : int(time.time()) at the moment of key generation
    """
    input_bits = _join_binary(
        _get_binary_md5(random_string),
        _get_binary_md5(str(utc_time)),
    )
    arr = np.array(input_bits)
    arr = tf.expand_dims(arr, axis=0)
    y = model.predict(arr, verbose=False)
    raw = np.array(y[0])
    mean = np.mean(raw)
    key_bits = ["1" if v > mean else "0" for v in raw]
    return _bin_to_hex("".join(key_bits))  # 64 hex chars = 256 bits


def encrypt_with_aes(message: str, aes_key_hex: str) -> str:
    """
    Encrypt *message* with the first 128 bits of *aes_key_hex* using AES-ECB.

    The plaintext is base64-encoded first, then zero-padded to a 16-byte
    boundary before encryption.  The returned value is a base64 string.
    """
    key_bytes = bytes.fromhex(aes_key_hex)[:16]  # 128-bit key
    cipher = AES.new(key_bytes, AES.MODE_ECB)
    msg_b64 = base64.b64encode(message.encode())
    block = 16
    pad_len = block - len(msg_b64) % block
    padded = msg_b64 + (chr(0) * pad_len).encode()
    return base64.b64encode(cipher.encrypt(padded)).decode()


def decrypt_with_aes(ciphertext_b64: str, aes_key_hex: str) -> str:
    """
    Decrypt a ciphertext produced by *encrypt_with_aes*.

    Returns the original plaintext string.
    """
    key_bytes = bytes.fromhex(aes_key_hex)[:16]
    cipher = AES.new(key_bytes, AES.MODE_ECB)
    enc = base64.b64decode(ciphertext_b64)
    decrypted = cipher.decrypt(enc)
    # Remove zero-byte padding (find last non-null sequence boundary)
    last = decrypted[-1:]
    idx = decrypted.rfind(last)
    unpadded = decrypted[:idx]
    return base64.b64decode(unpadded).decode()
