# SC-erp-migration-proto  

**Seguridad en la Computación | Trabajo Final**

---

## 🧩 Descripción del Proyecto

Este prototipo fue desarrollado como parte del curso **Seguridad en la Computación**, con el objetivo de **simular la migración segura de datos ERP bancarios desde un entorno local hacia la nube (Google Cloud Platform - GCP)**.

El enfoque del trabajo está centrado en la **gestión de credenciales y accesos** durante la migración, aplicando conceptos de seguridad como:
- Uso de **HashiCorp Vault** para el almacenamiento seguro de secretos.
- **Autenticación basada en tokens** para acceder a los secretos.
- **Separación de entornos locales y nube** para reducir exposición de claves.
- **Pipeline automatizado** que garantiza integridad y trazabilidad de los datos migrados.

---

## ⚙️ Arquitectura General

```text
┌─────────────────────┐
│     Local ERP DB    │
│ (simulada con CSVs) │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Pipeline seguro    │
│ (Python + Vault +   │
│  API GCS)           │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Google Cloud Storage│
│ (erp-migration-bucket)
└─────────────────────┘
```

---

## 🧰 Stack Tecnológico

| Componente | Tecnología | Uso |
|-------------|-------------|-----|
| Lenguaje principal | **Python 3.9+** | Scripts de migración y generación de datos |
| Seguridad / Secret Manager | **HashiCorp Vault** (en Docker) | Almacenamiento de credenciales GCP |
| Nube destino | **Google Cloud Storage (GCP)** | Destino de los archivos migrados |
| Entorno local | **Docker Desktop + PowerShell** | Ejecución controlada y aislada |
| Librerías Python | `requests`, `google-cloud-storage`, `faker`, `pandas`, `dotenv` | Migración, autenticación y generación de datasets |

---

## 🚀 Objetivo del Prototipo

**Simular un pipeline de migración seguro** desde datos ERP locales hacia GCP, aplicando buenas prácticas de seguridad en:
1. **Gestión de credenciales y secretos.**
2. **Autenticación y autorización controladas.**
3. **Validación y manejo de errores en el proceso de subida.**
4. **Uso responsable de entornos cloud.**

---

## 🧾 Estructura del Proyecto

```text
erp-migration-proto/
├─ docker/
│  └─ vault-policy.hcl
├─ secrets/
│  └─ gcp-sa.json                # Clave descargada desde GCP (Service Account)
├─ scripts/
│  ├─ generate_sample_csvs.py    # Genera datasets simulados ERP
│  └─ migrate_to_gcs.py          # Pipeline de migración seguro
├─ data/                         # CSVs generados localmente
├─ .env                          # Variables de entorno
├─ requirements.txt              # Dependencias Python
├─ docker-compose.yml            # Configuración de Vault
└─ README.md                     # Documentación del proyecto
```

---

## 🧩 Variables de Entorno (.env)

```bash
# Vault
VAULT_ADDR=http://127.0.0.1:8200
VAULT_TOKEN=root-token-demo
VAULT_SECRET_PATH=secret/data/erp/gcs-service-account

# GCP
GCS_BUCKET=erp-migration-bucket
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

### 6️⃣ Ejecutar el pipeline seguro
```powershell
python scripts/migrate_to_gcs.py
```
Migrará todos los CSV a GCP (`gs://erp-migration-bucket/migracion/`).

### 7️⃣ Verificar en GCP
Ir a [https://console.cloud.google.com/storage/browser](https://console.cloud.google.com/storage/browser)  
y confirmar los archivos subidos.

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
