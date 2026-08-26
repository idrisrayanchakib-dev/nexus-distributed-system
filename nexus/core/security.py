import base64
import hashlib
import json
from typing import Any, Dict, Optional, Union

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class SecurityManager:
    """
    Handles cryptographic key derivation (PBKDF2HMAC), symmetric End-to-End Encryption
    (Fernet), and deterministic room fingerprinting for network isolation.
    """

    STATIC_SALT = b"nexus_p2p_distributed_chat_salt_v2"
    KDF_ITERATIONS = 100_000

    def __init__(self, password: str) -> None:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.STATIC_SALT,
            iterations=self.KDF_ITERATIONS,
        )
        self.key_bytes = kdf.derive(password.strip().encode("utf-8"))
        self.key = base64.urlsafe_b64encode(self.key_bytes)
        self.cipher = Fernet(self.key)

    def get_fingerprint(self) -> str:
        """Returns a 4-character deterministic room identifier derived from key bytes."""
        return hashlib.sha256(self.key_bytes).hexdigest()[:4].upper()

    def encrypt(self, data_dict: Dict[str, Any]) -> str:
        """Serializes dictionary to JSON and encrypts with Fernet."""
        serialized = json.dumps(data_dict).encode("utf-8")
        return self.cipher.encrypt(serialized).decode("utf-8")

    def decrypt(self, encrypted_str: str) -> Union[Dict[str, Any], str]:
        """
        Decrypts Fernet ciphertext back into a dictionary.
        Returns 'WRONG_KEY' or 'CORRUPTED' upon failure.
        """
        try:
            decrypted_bytes = self.cipher.decrypt(encrypted_str.encode("utf-8"))
            return json.loads(decrypted_bytes.decode("utf-8"))
        except InvalidToken:
            return "WRONG_KEY"
        except Exception:
            return "CORRUPTED"
