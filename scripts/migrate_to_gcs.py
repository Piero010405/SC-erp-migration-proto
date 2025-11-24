# scripts/migrate_to_gcs.py
import os
import json
import time
import logging
import base64
from glob import glob
from tempfile import NamedTemporaryFile
from dotenv import load_dotenv
import requests

# módulos GCP
from google.cloud import storage
from google.cloud import kms_v1
from encryption_utils import generate_dek, encrypt_dek_with_kms, encrypt_file_aes_gcm, save_base64_file


# ---------------- CONFIG ----------------
load_dotenv(".env")

VAULT_ADDR = os.getenv("VAULT_ADDR", "http://127.0.0.1:8200")
VAULT_TOKEN = os.getenv("VAULT_TOKEN", "root-token-demo")
VAULT_SECRET_PATH = os.getenv("VAULT_SECRET_PATH", "secret/data/erp/gcs-service-account")

GCS_BUCKET = os.getenv("GCS_BUCKET")
KMS_KEY_NAME = os.getenv('KMS_KEY_NAME')
CSV_DIR = os.getenv("CSV_DIR", "data")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
RETRY_COUNT = int(os.getenv("RETRY_COUNT", 3))
RETRY_BACKOFF_SEC = int(os.getenv("RETRY_BACKOFF_SEC", 2))

logging.basicConfig(level=getattr(logging, LOG_LEVEL))
logger = logging.getLogger('migrator')

# ---------------------------------------

def get_secret_from_vault(path):
    url = f"{VAULT_ADDR}/v1/{path}"
    headers = {"X-Vault-Token": VAULT_TOKEN}
    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    return r.json()['data']['data']

def write_temp_sa_file(sa_json):
    tmp = NamedTemporaryFile(delete=False, suffix='.json')
    with open(tmp.name, 'w', encoding='utf-8') as f:
        json.dump(sa_json if isinstance(sa_json, dict) else json.loads(sa_json),f)
    return tmp.name

def ensure_bucket(client, bucket_name):
    bucket = client.bucket(bucket_name)
    if not bucket.exists():
        bucket = client.create_bucket(bucket_name)
    return bucket

def upload_blob_from_file(client, bucket_name, local_path, dest_name):
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(dest_name)
    blob.upload_from_filename(local_path)
    logger.info(f"Uploaded to gs://{bucket_name}/{dest_name}")
    return blob

def main():
    logger.info('Starting migration with envelope encryption')

    # 1) Obtener credencial GCP desde Vault
    logger.info('Retrieving GCP service account from Vault...')
    secret = get_secret_from_vault(VAULT_SECRET_PATH)
    if 'gcp_service_account_json' not in secret:
        logger.error('gcp_service_account_json not found in Vault secret')
        return 1

    sa_json = secret['gcp_service_account_json']
    sa_path = write_temp_sa_file(sa_json)
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = sa_path

    # 2) Inicializar clientes GCP
    storage_client = storage.Client()
    kms_client = kms_v1.KeyManagementServiceClient()

    # 3) asegurar bucket
    ensure_bucket(storage_client, GCS_BUCKET)

    # 4) procesar archivos
    csv_files = sorted(glob(os.path.join(CSV_DIR, '*.csv')))
    if not csv_files:
        logger.warning('No CSV files found')
        return 0

    for csv_path in csv_files:
        filename = os.path.basename(csv_path)
        base = os.path.splitext(filename)[0]
        logger.info(f'Processing {filename}')

        # Generar DEK local (256 bits)
        dek = generate_dek(32)

        # Cifrar DEK con KMS (KEK)
        dek_ciphertext = encrypt_dek_with_kms(kms_client, KMS_KEY_NAME, dek)

        # Cifrar archivo con DEK (AES-GCM)
        enc_path = os.path.join('data', f'{base}.enc')
        metadata = encrypt_file_aes_gcm(csv_path, enc_path, dek)

        # Guardar DEK cifrada (base64), metadata JSON y subir todo
        dek_b64_path = os.path.join('data', f'{base}.dek.enc.b64')
        save_base64_file(dek_b64_path, dek_ciphertext)
        metadata_path = os.path.join('data', f'{base}.metadata.json')

        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)

        # Subir archivos a GCS
        try:
            upload_blob_from_file(storage_client, GCS_BUCKET, enc_path,f'migration/encrypted_files/{base}.enc')
            upload_blob_from_file(storage_client, GCS_BUCKET, dek_b64_path,f'migration/encrypted_dek/{base}.dek.b64')
            upload_blob_from_file(storage_client, GCS_BUCKET, metadata_path,f'migration/metadata/{base}.metadata.json')
            logger.info(f'Successfully migrated {filename}')
        except Exception as e:
            logger.exception(f'Failed to upload {filename}: {e}')

    # Cleanup temp SA file
    try:
        os.remove(sa_path)
    except Exception:
        pass
    
    logger.info('Migration complete')
    return 0

if __name__ == '__main__':
    exit(main())
