"""
ClaimSense.ai - Encryption Service

Provides AES encryption for patient PII fields in claim data.
Uses Fernet symmetric encryption with a key derived from the application SECRET_KEY.

PII fields protected:
- patient.name, patient.dob, patient.phone
- patient.email, patient.abha_id, patient.policy_number

Usage:
    from services.encryption_service import encrypt_claim_pii, decrypt_claim_pii

    encrypted_claim = encrypt_claim_pii(claim)   # Before storage
    decrypted_claim = decrypt_claim_pii(claim)   # After retrieval
"""

import base64
import logging
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

from config import get_settings
from models.claim_schema import ClaimSchema

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PII fields to encrypt/decrypt on the patient object
# ---------------------------------------------------------------------------
PII_FIELDS = ["name", "dob", "phone", "email", "abha_id", "policy_number"]

# ---------------------------------------------------------------------------
# Fernet instance (lazy-init singleton)
# ---------------------------------------------------------------------------
_fernet_instance: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    """
    Create and cache a Fernet encryption instance.

    Key is derived from SECRET_KEY in config using PBKDF2-HMAC-SHA256.
    The same SECRET_KEY always produces the same encryption key,
    so data encrypted in one session can be decrypted in another
    as long as the SECRET_KEY hasn't changed.
    """
    global _fernet_instance
    if _fernet_instance is not None:
        return _fernet_instance

    settings = get_settings()
    secret = settings.SECRET_KEY

    if not secret or secret == "dev-secret-key-change-in-production":
        logger.warning(
            "Using default SECRET_KEY for encryption. "
            "Set a strong SECRET_KEY in .env for production use."
        )

    # Derive a 32-byte key from SECRET_KEY using PBKDF2
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"claimsense-ai-v1",  # Static salt is acceptable for MVP
        iterations=480_000,
    )
    derived_key = kdf.derive(secret.encode("utf-8"))
    fernet_key = base64.urlsafe_b64encode(derived_key)

    _fernet_instance = Fernet(fernet_key)
    logger.info("Encryption service initialized")
    return _fernet_instance


# ---------------------------------------------------------------------------
# Field-level encrypt / decrypt
# ---------------------------------------------------------------------------

def encrypt_field(value: Optional[str]) -> Optional[str]:
    """
    Encrypt a single string value.

    Returns None if input is None, empty string if input is empty.
    Otherwise returns base64-encoded ciphertext.
    """
    if value is None:
        return None
    if value == "":
        return ""

    fernet = _get_fernet()
    encrypted = fernet.encrypt(value.encode("utf-8"))
    return encrypted.decode("utf-8")


def decrypt_field(encrypted: Optional[str]) -> Optional[str]:
    """
    Decrypt a single encrypted string value.

    Returns None if input is None, empty string if input is empty.

    Raises:
        ValueError: If decryption fails (wrong key or corrupted data).
    """
    if encrypted is None:
        return None
    if encrypted == "":
        return ""

    fernet = _get_fernet()
    try:
        decrypted = fernet.decrypt(encrypted.encode("utf-8"))
        return decrypted.decode("utf-8")
    except InvalidToken:
        raise ValueError(
            "Failed to decrypt field - key mismatch or corrupted data. "
            "Ensure SECRET_KEY has not changed since encryption."
        )


# ---------------------------------------------------------------------------
# Claim-level encrypt / decrypt (all PII fields at once)
# ---------------------------------------------------------------------------

def encrypt_claim_pii(claim: ClaimSchema) -> ClaimSchema:
    """
    Encrypt all PII fields in a claim's patient object.

    Returns a deep copy of the claim with encrypted patient fields.
    The original claim object is NOT modified.

    Encrypted fields: name, dob, phone, email, abha_id, policy_number
    """
    encrypted = claim.model_copy(deep=True)

    for field in PII_FIELDS:
        original_value = getattr(encrypted.patient, field, None)
        if original_value is not None and original_value != "":
            encrypted_value = encrypt_field(original_value)
            setattr(encrypted.patient, field, encrypted_value)

    logger.info(
        "Encrypted PII for claim %s (%d fields processed)",
        claim.claim_id or "unknown",
        len(PII_FIELDS),
    )
    return encrypted


def decrypt_claim_pii(claim: ClaimSchema) -> ClaimSchema:
    """
    Decrypt all PII fields in a claim's patient object.

    Returns a deep copy of the claim with decrypted patient fields.
    The original claim object is NOT modified.

    Raises:
        ValueError: If any field cannot be decrypted.
    """
    decrypted = claim.model_copy(deep=True)

    for field in PII_FIELDS:
        encrypted_value = getattr(decrypted.patient, field, None)
        if encrypted_value is not None and encrypted_value != "":
            try:
                decrypted_value = decrypt_field(encrypted_value)
                setattr(decrypted.patient, field, decrypted_value)
            except ValueError:
                logger.error(
                    "Failed to decrypt field '%s' for claim %s",
                    field,
                    claim.claim_id or "unknown",
                )
                raise

    logger.info(
        "Decrypted PII for claim %s (%d fields processed)",
        claim.claim_id or "unknown",
        len(PII_FIELDS),
    )
    return decrypted
