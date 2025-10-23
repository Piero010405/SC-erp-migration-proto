import os
import json
import requests
from dotenv import load_dotenv

load_dotenv('../.env') if os.path.exists('../.env') else load_dotenv('.env')

VAULT_ADDR = os.getenv("VAULT_ADDR")
VAULT_TOKEN = os.getenv("VAULT_TOKEN")
VAULT_SECRET_PATH = os.getenv("VAULT_SECRET_PATH", "secret/data/erp/gcs-service-account")

CSV_FILE = os.getenv("CSV_FILE", "data/sample_erp_data.csv")

# MinIO / S3 configs (local)
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "migration-bucket")

# GCS configs
GCS_BUCKET = os.getenv("GCS_BUCKET")

def get_secret_from_vault(path):
    # expects KV v2: secret/data/<path>
    url = f"{VAULT_ADDR}/v1/{path}"
    headers = {"X-Vault-Token": VAULT_TOKEN}
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    data = r.json()
    # data['data']['data'] contains the secret map
    return data["data"]["data"]

def upload_to_minio(local_path, bucket, object_name):
    import boto3
    s3 = boto3.resource('s3',
                        endpoint_url=MINIO_ENDPOINT,
                        aws_access_key_id=MINIO_ACCESS_KEY,
                        aws_secret_access_key=MINIO_SECRET_KEY)
    # create bucket if not exists
    try:
        s3.create_bucket(Bucket=bucket)
    except Exception as e:
        pass
    s3.Bucket(bucket).upload_file(local_path, object_name)
    print(f"Uploaded {local_path} to MinIO bucket {bucket}/{object_name}")

def upload_to_gcs(local_path, bucket, object_name):
    from google.cloud import storage
    client = storage.Client()
    bucket = client.bucket(bucket)
    blob = bucket.blob(object_name)
    blob.upload_from_filename(local_path)
    print(f"Uploaded {local_path} to GCS bucket {bucket.name}/{object_name}")

def main():
    # --- step 1: obtain secret from Vault (simulate policy enforcement)
    print("[*] Getting secret from Vault...")
    try:
        secret = get_secret_from_vault(VAULT_SECRET_PATH)
    except Exception as e:
        print("[!] Error getting secret from Vault:", e)
        return

    # secret may contain either minio credentials or gcp service account json
    if "minio_access_key" in secret:
        print("[*] Using MinIO credentials retrieved from Vault.")
        # use values from vault (overwrite envs)
        os.environ["MINIO_ACCESS_KEY"] = secret.get("minio_access_key")
        os.environ["MINIO_SECRET_KEY"] = secret.get("minio_secret_key")
        # use endpoint from .env_secret or from secret
        endpoint = secret.get("minio_endpoint") or MINIO_ENDPOINT
        os.environ["MINIO_ENDPOINT"] = endpoint
        upload_to_minio(CSV_FILE, MINIO_BUCKET, "migracion/" + os.path.basename(CSV_FILE))
    elif "gcp_service_account_json" in secret:
        print("[*] Using GCP service account JSON retrieved from Vault.")
        # write JSON to a temp file and set GOOGLE_APPLICATION_CREDENTIALS
        sa_json = secret.get("gcp_service_account_json")
        sa_path = "secrets/gcp-sa-from-vault.json"
        os.makedirs("secrets", exist_ok=True)
        with open(sa_path, "w") as f:
            json.dump(sa_json if isinstance(sa_json, dict) else json.loads(sa_json), f)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = sa_path
        upload_to_gcs(CSV_FILE, GCS_BUCKET, "migracion/" + os.path.basename(CSV_FILE))
    else:
        print("[!] Secret format unknown. secret keys:", secret.keys())

if __name__ == "__main__":
    main()
