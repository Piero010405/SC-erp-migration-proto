# scripts/migrate_to_gcs.py
import os
import json
import time
import logging
import hashlib
import requests
from glob import glob
from tempfile import NamedTemporaryFile

from dotenv import load_dotenv
load_dotenv('.env')

# Config
VAULT_ADDR = os.getenv("VAULT_ADDR")
VAULT_TOKEN = os.getenv("VAULT_TOKEN")
VAULT_SECRET_PATH = os.getenv("VAULT_SECRET_PATH", "secret/data/erp/gcs-service-account")
GCS_BUCKET = os.getenv("GCS_BUCKET")
CSV_DIR = os.getenv("CSV_DIR", "data")
RETRY_COUNT = int(os.getenv("RETRY_COUNT", "3"))
RETRY_BACKOFF_SEC = int(os.getenv("RETRY_BACKOFF_SEC", "2"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Logging
logging.basicConfig(level=getattr(logging, LOG_LEVEL))
logger = logging.getLogger("migrator")

def get_secret_from_vault(path):
    url = f"{VAULT_ADDR}/v1/{path}"
    headers = {"X-Vault-Token": VAULT_TOKEN}
    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    resp = r.json()
    return resp["data"]["data"]

def write_temp_sa_file(sa_json):
    # sa_json may be a dict or a stringified JSON
    if isinstance(sa_json, str):
        try:
            sa_obj = json.loads(sa_json)
        except Exception:
            raise ValueError("gcp_service_account_json in Vault is not valid JSON")
    else:
        sa_obj = sa_json
    tmp = NamedTemporaryFile(delete=False, suffix=".json")
    with open(tmp.name, "w", encoding="utf-8") as f:
        json.dump(sa_obj, f)
    return tmp.name

def md5_of_file(path):
    md5 = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            md5.update(chunk)
    return md5.digest()

def upload_file_to_gcs(local_path, bucket_name, dest_name, client):
    from google.cloud import storage
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(dest_name)
    blob.upload_from_filename(local_path)
    # fetch metadata to verify
    blob.reload()
    return blob

def main():
    # --- 1. get SA json from Vault
    logger.info("Retrieving service account from Vault...")
    try:
        secret = get_secret_from_vault(VAULT_SECRET_PATH)
    except Exception as e:
        logger.exception("Failed to get secret from Vault: %s", e)
        return 1

    if "gcp_service_account_json" not in secret:
        logger.error("Vault secret does not contain 'gcp_service_account_json' key. Keys: %s", list(secret.keys()))
        return 2

    sa_json = secret["gcp_service_account_json"]

    # write temp SA file
    try:
        sa_path = write_temp_sa_file(sa_json)
    except Exception as e:
        logger.exception("Error writing temp SA file: %s", e)
        return 3

    # set GOOGLE_APPLICATION_CREDENTIALS for client libraries
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = sa_path

    # initialize GCS client
    try:
        from google.cloud import storage
        client = storage.Client()
    except Exception as e:
        logger.exception("Failed to initialize GCS client: %s", e)
        os.remove(sa_path)
        return 4

    # prepare file list
    csv_files = sorted(glob(os.path.join(CSV_DIR, "*.csv")))
    if not csv_files:
        logger.warning("No CSV files found in %s", CSV_DIR)
        os.remove(sa_path)
        return 0

    # ensure bucket exists (try to create if missing)
    try:
        bucket = client.bucket(GCS_BUCKET)
        if not bucket.exists():
            logger.info("Bucket %s does not exist. Creating...", GCS_BUCKET)
            client.create_bucket(GCS_BUCKET)
            logger.info("Bucket created: %s", GCS_BUCKET)
    except Exception as e:
        logger.exception("Problem ensuring bucket exists: %s", e)
        os.remove(sa_path)
        return 5

    # process files
    for path in csv_files:
        name = os.path.basename(path)
        dest = f"migracion/{name}"
        logger.info("Uploading %s -> gs://%s/%s", path, GCS_BUCKET, dest)
        success = False
        attempt = 0
        last_error = None
        file_md5 = md5_of_file(path)
        while attempt < RETRY_COUNT and not success:
            try:
                attempt += 1
                blob = upload_file_to_gcs(path, GCS_BUCKET, dest, client)
                # verify size or md5 (blob.md5_hash is base64; local md5 is binary)
                remote_md5_b64 = blob.md5_hash  # base64
                if not remote_md5_b64:
                    logger.warning("Remote MD5 not available, verifying size instead")
                    if blob.size == os.path.getsize(path):
                        success = True
                    else:
                        raise RuntimeError("Size mismatch after upload")
                else:
                    import base64
                    local_b64 = base64.b64encode(file_md5).decode()
                    if local_b64 == remote_md5_b64:
                        success = True
                    else:
                        raise RuntimeError("MD5 mismatch: local %s remote %s" % (local_b64, remote_md5_b64))
                logger.info("Upload verified for %s", name)
            except Exception as e:
                last_error = e
                logger.warning("Attempt %d failed for %s: %s", attempt, name, e)
                time.sleep(RETRY_BACKOFF_SEC * attempt)
        if not success:
            logger.error("Failed to upload %s after %d attempts. Last error: %s", name, RETRY_COUNT, last_error)
        else:
            logger.info("Successfully migrated %s", name)

    # cleanup SA temp
    try:
        os.remove(sa_path)
    except Exception:
        logger.warning("Failed to remove temp SA file %s", sa_path)

    logger.info("Migration complete.")
    return 0

if __name__ == "__main__":
    exit(main())
