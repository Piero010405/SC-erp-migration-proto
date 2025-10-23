# scripts/migrate_to_gcs.py
import os
import json
import requests
import time
from dotenv import load_dotenv
from google.cloud import storage

# ---------------- CONFIG ----------------
load_dotenv(".env")

VAULT_ADDR = os.getenv("VAULT_ADDR", "http://127.0.0.1:8200")
VAULT_TOKEN = os.getenv("VAULT_TOKEN", "root-token-demo")
VAULT_SECRET_PATH = os.getenv("VAULT_SECRET_PATH", "secret/data/erp/gcs-service-account")

CSV_DIR = os.getenv("CSV_DIR", "data")
GCS_BUCKET = os.getenv("GCS_BUCKET")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
RETRY_COUNT = int(os.getenv("RETRY_COUNT", 3))
RETRY_BACKOFF_SEC = int(os.getenv("RETRY_BACKOFF_SEC", 2))

# ---------------------------------------

def log(msg):
    print(f"[{LOG_LEVEL}] {msg}")

def get_secret_from_vault(path):
    """Obtiene el JSON de servicio desde Vault."""
    url = f"{VAULT_ADDR}/v1/{path}"
    headers = {"X-Vault-Token": VAULT_TOKEN}
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    data = r.json()
    return data["data"]["data"]

def upload_to_gcs(local_path, bucket_name, blob_name):
    """Sube un archivo a Google Cloud Storage con reintentos."""
    for attempt in range(1, RETRY_COUNT + 1):
        try:
            client = storage.Client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            blob.upload_from_filename(local_path)
            log(f"✅ Subido: {blob_name}")
            return
        except Exception as e:
            log(f"[!] Error subiendo {local_path} (intento {attempt}/{RETRY_COUNT}): {e}")
            time.sleep(RETRY_BACKOFF_SEC)
    raise RuntimeError(f"No se pudo subir {local_path} después de {RETRY_COUNT} intentos.")

def main():
    log("Obteniendo credencial GCP desde Vault...")
    secret = get_secret_from_vault(VAULT_SECRET_PATH)

    if "gcp_service_account_json" not in secret:
        raise ValueError("❌ Secret incorrecto o mal formateado en Vault.")

    sa_json = secret["gcp_service_account_json"]

    os.makedirs("secrets", exist_ok=True)
    sa_path = "secrets/gcp-sa-from-vault.json"
    with open(sa_path, "w") as f:
        json.dump(sa_json, f)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = sa_path

    log("Credenciales GCP configuradas correctamente.")
    log("Buscando archivos CSV en ./data...")

    csv_files = [f for f in os.listdir(CSV_DIR) if f.endswith(".csv")]
    if not csv_files:
        raise FileNotFoundError("No se encontraron archivos CSV para migrar.")

    for csv_file in csv_files:
        local_path = os.path.join(CSV_DIR, csv_file)
        object_name = f"migracion/{csv_file}"
        upload_to_gcs(local_path, GCS_BUCKET, object_name)

    log("✔ Migración completa de todos los archivos CSV.")

if __name__ == "__main__":
    main()
