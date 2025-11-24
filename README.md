# 📘 SC-erp-migration-proto

**Seguridad en la Computación | Trabajo Final**

---

## 🧩 Descripción del Proyecto

Este prototipo fue desarrollado como parte del curso **Seguridad en la Computación**, con el objetivo de **simular un pipeline seguro de migración de datos ERP** desde un entorno local hacia **Google Cloud Platform (GCP)** utilizando buenas prácticas de seguridad modernas.

La solución implementada integra:

- **Cifrado con Envelope Encryption (DEK + KMS)**  
- **Gestión de secretos con HashiCorp Vault**  
- **Service Accounts con privilegios mínimos en GCP**  
- **Pipeline automatizado en Python**, robusto y auditable  
- **Subida final a Google Cloud Storage (GCS)** validando integridad y seguridad extremo a extremo  

Todo el proceso refleja estándares recomendados por **NIST**, **Google Cloud Security Foundations** y prácticas corporativas para migración de datos sensibles.

---

## ⚙️ Arquitectura General

```text
┌─────────────────────┐
│ Datos ERP locales │
│ (archivos CSV) │
└─────────┬───────────┘
│
▼
┌─────────────────────────┐
│ Pipeline seguro Python │
│ 1. Obtiene credenciales │
│ desde Vault │
│ 2. Genera DEK local │
│ 3. Cifra DEK con KMS │
│ 4. Cifra CSV con AES-GCM│
│ 5. Sube .enc + DEK + │
│ metadata a GCS │
└─────────┬───────────────┘
│
▼
┌─────────────────────────┐
│ Google Cloud Storage │
│ /migration │
│ ├─ encrypted_files │
│ ├─ encrypted_dek │
│ └─ metadata │
└─────────────────────────┘
```

---

## 🧰 Stack Tecnológico

| Componente | Tecnología | Justificación |
|-----------|------------|---------------|
| **Lenguaje / Scripts** | Python 3.10+ | Flexibilidad, librerías oficiales GCP, maduro para pipelines |
| **Gestión de secretos** | HashiCorp Vault | Estándar de la industria, evita exponer claves en .env o código |
| **Cifrado** | Google Cloud KMS | Cifrado gestionado, claves rotables, auditoría nativa |
| **Almacenamiento** | Google Cloud Storage | Durable, seguro, IAM granular |
| **Contenedores** | Docker + Docker Compose | Aislamiento y reproducibilidad |
| **Librerías Python** | `google-cloud-storage`, `google-cloud-kms`, `cryptography`, `faker` | Soporte oficial y robustez |
| **Autenticación** | Service Accounts | Seguridad basada en identidad |

---

## 🚀 Objetivo del Prototipo

El pipeline demuestra:

- **Migración segura de información sensible (ERP)**
- **Cifrado por capas (Envelope Encryption)**
- **Autorización de acceso estricta**
- **Aislamiento de secretos via Vault**
- **Verificación completa de subida a GCS**

---

## 🧾 Estructura del Proyecto

```text
erp-migration-proto/
├─ docker/
│ └─ vault-policy.hcl
├─ secrets/
│ └─ gcp-sa.json
├─ scripts/
│ ├─ generate_sample_csvs.py
│ ├─ migrate_to_gcs.py
│ └─ encryption_utils.py
├─ data/
│ └─ *.csv
├─ .env
├─ requirements.txt
├─ docker-compose.yml
└─ README.md
```

---

## 🧩 Variables de Entorno (.env)

```bash
# Vault
# Vault
VAULT_ADDR=http://127.0.0.1:8200
VAULT_TOKEN=root-token-demo
VAULT_SECRET_PATH=secret/data/erp/gcs-service-account

# GCP
GCS_BUCKET=erp-secure-bucket
KMS_KEY_NAME=projects/PROJECT_ID/locations/us-central1/keyRings/erp-keyring/cryptoKeys/erp-kek
CSV_DIR=data

# Script runtime
LOG_LEVEL=INFO
RETRY_COUNT=3
RETRY_BACKOFF_SEC=2
```

---

## 🧠 Paso a Paso — Ejecución Completa

### 1️⃣ Clonar el repositorio
```bash
git clone https://github.com/usuario/SC-erp-migration-proto.git
cd SC-erp-migration-proto
```

### 2️⃣ Crear entorno virtual e instalar dependencias
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3️⃣ Levantar HashiCorp Vault
```powershell
docker-compose up -d
```
Abrir interfaz web:  
👉 [http://127.0.0.1:8200/ui](http://127.0.0.1:8200/ui)  
Token: `root-token-demo`

### 4️⃣ Subir la credencial de GCP al Vault
```powershell
$VAULT_ADDR = "http://127.0.0.1:8200"
$VAULT_TOKEN = "root-token-demo"
$payload = Get-Content secrets/gcp-sa.json -Raw | ConvertFrom-Json
$body = @{ data = @{ gcp_service_account_json = $payload } } | ConvertTo-Json -Depth 5

Invoke-RestMethod -Uri "$VAULT_ADDR/v1/secret/data/erp/gcs-service-account" `
    -Headers @{ "X-Vault-Token" = $VAULT_TOKEN } `
    -Method POST -ContentType "application/json" -Body $body
```

### 5️⃣ Generar datasets simulados
```powershell
python scripts/generate_sample_csvs.py
```
Se crean 10 archivos en `data/erp_data_01.csv` … `erp_data_10.csv`.

### 6️⃣ Migración Exitosa y Validación Final
Una vez configurados GCP, Vault, las keys KMS y los secretos, se ejecutó el pipeline:
```powershell
python scripts/migrate_to_gcs.py
```
El pipeline procesó:

- 10 datasets ERP: erp_data_01.csv … erp_data_10.csv
- 1 dataset adicional: sample_erp_data.csv
- Y para cada archivo se generaron:

| Tipo de archivo   | Contenido                       | Carpeta destino              |
| ----------------- | ------------------------------- | ---------------------------- |
| `*.enc`           | archivo ERP cifrado con AES-GCM | `migration/encrypted_files/` |
| `*.dek.b64`       | DEK cifrada con KEK (KMS)       | `migration/encrypted_dek/`   |
| `*.metadata.json` | nonce, tag GCM y parámetros     | `migration/metadata/`        |


### 7️⃣ Verificar en GCP
Ir a [https://console.cloud.google.com/storage/browser](https://console.cloud.google.com/storage/browser)  
y confirmar los archivos subidos.

La estructura final en GCS quedó así:

```text
gs://erp-secure-bucket/migration/
│
├─ encrypted_files/
│    ├─ erp_data_01.enc
│    ├─ ...
├─ encrypted_dek/
│    ├─ erp_data_01.dek.b64
│    ├─ ...
└─ metadata/
     ├─ erp_data_01.metadata.json
     ├─ ...
```

### 8️⃣ (Opcional) Apagar y limpiar

```powershell
docker-compose down
```

---

## 🔐 Estándares y Buenas Prácticas Aplicadas

| Concepto de Seguridad | Implementación |
|-----------------------|----------------|
| **Gestión de secretos centralizada** | HashiCorp Vault almacena las claves del servicio GCP |
| **Autenticación basada en tokens** | `VAULT_TOKEN` controla el acceso al Secret Manager |
| **Principio de mínimo privilegio** | Service Account GCP con permisos `Storage Object Admin` únicamente |
| **Separación de entornos** | Claves fuera del código fuente (.env + Vault) |
| **Resiliencia y confiabilidad** | Retries, backoff y validación de subida |
| **Auditoría** | Logs de operaciones y trazabilidad por archivo subido |

---

## 🧾 Créditos

- **Autores:** Grupo de Seguridas (Hello Kity)
- **Universidad:** USIL  
- **Curso:** Seguridad en la Computación
- **Año:** 2025

---

## 📄 Licencia

Este proyecto es académico y se distribuye bajo la licencia **MIT**, únicamente con fines educativos.
