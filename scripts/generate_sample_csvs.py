# scripts/generate_sample_csvs.py
import csv
import os
from datetime import datetime, timedelta
from random import randint, choice, uniform
import faker

os.makedirs("data", exist_ok=True)
fake = faker.Faker("es_ES")

CURRENCIES = ["PEN", "USD", "EUR"]
BRANCHES = ["LIMA-CENTRO", "AREQUIPA", "CUSCO", "TRUJILLO", "CHICLAYO"]

def generate_row(idx, start_date):
    cliente_id = randint(1000000, 9999999)
    return {
        "record_id": idx,
        "branch": choice(BRANCHES),
        "client_id": cliente_id,
        "client_name": fake.company(),
        "document_type": choice(["DNI", "RUC", "PASAPORTE"]),
        "document_id": str(randint(10000000, 99999999)),
        "amount": f"{round(uniform(100.0, 10000.0), 2)}",
        "currency": choice(CURRENCIES),
        "date": (start_date + timedelta(days=randint(0,30))).strftime("%Y-%m-%d"),
        "erp_table": choice(["invoices","payments","customers"])
    }

def create_csv(file_path, rows=200, start_id=1, start_date=None):
    if start_date is None:
        start_date = datetime(2025, 9, 1)
    with open(file_path, "w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "record_id","branch","client_id","client_name","document_type","document_id","amount","currency","date","erp_table"
        ])
        writer.writeheader()
        for i in range(start_id, start_id + rows):
            writer.writerow(generate_row(i, start_date))

if __name__ == "__main__":
    base_start = 1
    for n in range(1, 11):
        fname = f"data/erp_data_{n:02d}.csv"
        create_csv(fname, rows=150, start_id=base_start, start_date=datetime(2025,9,1))
        base_start += 150
    print("10 CSVs generated in ./data")
