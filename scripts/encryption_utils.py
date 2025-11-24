# scripts/encryption_utils.py
import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from google.cloud import kms_v1

def generate_dek(length=32):
    """Genera un DEK de `length` bytes (por defecto 32 bytes = 256 bits)."""
    return os.urandom(length)

def encrypt_dek_with_kms(kms_client: kms_v1.KeyManagementServiceClient,
    key_name: str, dek: bytes) -> bytes:
    """Cifra la DEK con la KEK en Cloud KMS y devuelve el ciphertext (bytes).
    kms_client: instancia de KeyManagementServiceClient
    key_name: nombre completo del cryptoKey en KMS
    dek: bytes
    """
    # KMS encrypt API -> returns EncryptResponse with ciphertext bytes
    resp = kms_client.encrypt(request={"name": key_name, "plaintext": dek})

    return resp.ciphertext

def decrypt_dek_with_kms(kms_client: kms_v1.KeyManagementServiceClient,
    key_name: str, dek_ciphertext: bytes) -> bytes:
    """Descifra la DEK usando KMS (para uso en GCP)."""
    resp = kms_client.decrypt(request={"name": key_name, "ciphertext":
    dek_ciphertext})
    return resp.plaintext

def encrypt_file_aes_gcm(input_path: str, output_path: str, dek: bytes) -> dict:
    """Cifra el archivo `input_path` con AES-256-GCM usando `dek`.
    Escribe el ciphertext en `output_path` (binario). Retorna metadata dict con
    nonce y sizes (base64 nonce).
    """
    aesgcm = AESGCM(dek)
    nonce = os.urandom(12) # 96-bit nonce para AES-GCM
    with open(input_path, "rb") as f:
        plaintext = f.read()

    ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data=None)
    with open(output_path, "wb") as f:
        f.write(ciphertext)

    metadata = {
    "nonce_b64": base64.b64encode(nonce).decode("utf-8"),
    "plaintext_size": len(plaintext),
    "ciphertext_size": len(ciphertext),
    "algorithm": "AES-256-GCM"
    }
    return metadata

def save_base64_file(path: str, data: bytes):
    """Guarda `data` (bytes) en base64 en `path` (texto)."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(base64.b64encode(data).decode("utf-8"))

def load_base64_file(path: str) -> bytes:    
    with open(path, "r", encoding="utf-8") as f:
        return base64.b64decode(f.read())
