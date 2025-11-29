"""
Encryption utilities for secure credential storage.

Uses Fernet symmetric encryption for storing sensitive data like API keys.

:copyright: (c) 2025
:license: MIT
"""

import base64
import logging
import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class EncryptionManager:
    """
    Manages encryption/decryption of sensitive data.

    Uses Fernet (AES-128-CBC) for symmetric encryption.
    Key is derived from a master secret using PBKDF2.

    Example::

        manager = EncryptionManager("your-master-secret")
        encrypted = manager.encrypt("my-api-key")
        decrypted = manager.decrypt(encrypted)
    """

    def __init__(self, master_secret: Optional[str] = None) -> None:
        """
        Initialize encryption manager.

        :param master_secret: Master secret for key derivation.
            If not provided, uses ENCRYPTION_KEY env var.
        :type master_secret: Optional[str]
        """
        self._master_secret = master_secret or os.getenv(
            "ENCRYPTION_KEY",
            os.getenv("SECRET_KEY", "default-secret-change-in-production"),
        )
        self._fernet: Optional[Fernet] = None
        self._salt = os.getenv("ENCRYPTION_SALT", "trading-api-salt").encode()

    def _get_fernet(self) -> Fernet:
        """
        Get or create Fernet instance.

        :returns: Fernet encryption instance.
        :rtype: Fernet
        """
        if self._fernet is None:

            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=self._salt,
                iterations=480000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self._master_secret.encode()))
            self._fernet = Fernet(key)
        return self._fernet

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a string.

        :param plaintext: Text to encrypt.
        :type plaintext: str
        :returns: Base64-encoded encrypted text.
        :rtype: str
        """
        if not plaintext:
            return ""

        fernet = self._get_fernet()
        encrypted = fernet.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted).decode()

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt an encrypted string.

        :param ciphertext: Base64-encoded encrypted text.
        :type ciphertext: str
        :returns: Decrypted plaintext.
        :rtype: str
        :raises ValueError: If decryption fails.
        """
        if not ciphertext:
            return ""

        try:
            fernet = self._get_fernet()
            encrypted = base64.urlsafe_b64decode(ciphertext.encode())
            decrypted = fernet.decrypt(encrypted)
            return decrypted.decode()
        except InvalidToken:
            logger.error("Failed to decrypt: invalid token")
            raise ValueError("Decryption failed: invalid or corrupted data")
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise ValueError(f"Decryption failed: {e}")

    def is_encrypted(self, text: str) -> bool:
        """
        Check if text appears to be encrypted.

        :param text: Text to check.
        :type text: str
        :returns: True if text appears encrypted.
        :rtype: bool
        """
        if not text:
            return False

        try:

            decoded = base64.urlsafe_b64decode(text.encode())

            return len(decoded) > 0 and decoded[0:1] == b"g"
        except Exception:
            return False


_encryption_manager: Optional[EncryptionManager] = None


def get_encryption_manager() -> EncryptionManager:
    """
    Get global encryption manager.

    :returns: Encryption manager instance.
    :rtype: EncryptionManager
    """
    global _encryption_manager
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager()
    return _encryption_manager


def encrypt_credential(plaintext: str) -> str:
    """
    Encrypt a credential.

    :param plaintext: Credential to encrypt.
    :type plaintext: str
    :returns: Encrypted credential.
    :rtype: str
    """
    return get_encryption_manager().encrypt(plaintext)


def decrypt_credential(ciphertext: str) -> str:
    """
    Decrypt a credential.

    :param ciphertext: Encrypted credential.
    :type ciphertext: str
    :returns: Decrypted credential.
    :rtype: str
    """
    return get_encryption_manager().decrypt(ciphertext)
