# scripts/generate_sample_csvs.py
# scripts/generate_sample_csvs.py
import os
import pandas as pd
from faker import Faker
import random

fake = Faker()

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

def generate_erp_dataset(index: int, n_rows: int = 50):
    """Genera datos simulados de ERP bancario (clientes, transacciones, montos)."""
    records = []
    for _ in range(n_rows):
        record = {
            "id_cliente": fake.uuid4(),
            "nombre": fake.name(),
            "dni": fake.random_int(min=10000000, max=99999999),
            "fecha_transaccion": fake.date_this_year().strftime("%Y-%m-%d"),
            "tipo_transaccion": random.choice(["Deposito", "Retiro", "Pago de servicio", "Transferencia"]),
            "monto": round(random.uniform(10.0, 5000.0), 2),
            "moneda": random.choice(["PEN", "USD"]),
            "estado": random.choice(["Procesado", "Pendiente", "Fallido"]),
        }
        records.append(record)
    df = pd.DataFrame(records)
    file_path = os.path.join(DATA_DIR, f"erp_data_{index:02}.csv")
    df.to_csv(file_path, index=False, encoding="utf-8")
    print(f"✅ Generado {file_path} ({len(df)} filas)")
    return file_path


def main():
    print("[*] Generando archivos de datos simulados...")
    for i in range(1, 11):
        generate_erp_dataset(i)
    print("[✔] Generación completada. Archivos guardados en ./data/")


if __name__ == "__main__":
    main()
