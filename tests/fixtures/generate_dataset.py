import numpy as np
import pandas as pd
from faker import Faker
from datetime import datetime, timedelta
import random
import uuid
import os

# Configuración inicial y semilla para reproducibilidad
random.seed(42)
np.random.seed(42)
fake = Faker('es_MX')
fake.seed_instance(42)

TOTAL_ROWS = 10000
NORMAL_ROWS = 9700
ANOMALY_EACH = 60

normal_vendors = [f"Vendor_{i:03d}" for i in range(1, 21)]
departments = ['Operaciones', 'Ventas', 'RRHH', 'Finanzas', 'TI']
accounts = ['4000-Ventas', '5100-Gastos_Op', '5200-Nomina', '6000-Marketing', '2000-Cuentas_Pag']

data = []

def random_normal_date() -> datetime:
    """Genera una fecha aleatoria entre lunes y viernes, 8:00 a 18:00 en 2024."""
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 12, 31)
    
    while True:
        delta = random.random() * (end_date - start_date)
        dt = start_date + delta
        if dt.weekday() < 5 and 8 <= dt.hour < 18:
            return dt

# 1. 9700 Transacciones Normales
for _ in range(NORMAL_ROWS):
    dt = random_normal_date()
    amount = np.random.lognormal(mean=8, sigma=1.5)
    amount = round(min(max(amount, 10.0), 100000.0), 2)
    
    data.append({
        'id': str(uuid.uuid4()),
        'date': dt.isoformat(),
        'amount': amount,
        'currency': 'USD',
        'account_debit': random.choice(accounts),
        'account_credit': '1000-Banco',
        'description': fake.sentence(nb_words=4),
        'vendor_id': random.choice(normal_vendors),
        'employee_id': f"EMP_{random.randint(100, 999)}",
        'department': random.choice(departments),
        'source_system': 'csv',
        'is_anomaly': 0
    })

# 2. 60 ROUND_AMOUNT (> 10000, exactamente redondos)
for _ in range(ANOMALY_EACH):
    dt = random_normal_date()
    amount = float(random.randint(11, 50) * 1000)
    data.append({
        'id': str(uuid.uuid4()),
        'date': dt.isoformat(),
        'amount': amount,
        'currency': 'USD',
        'account_debit': random.choice(accounts),
        'account_credit': '1000-Banco',
        'description': "Pago de consultoría (redondeado)",
        'vendor_id': random.choice(normal_vendors),
        'employee_id': f"EMP_{random.randint(100, 999)}",
        'department': random.choice(departments),
        'source_system': 'csv',
        'is_anomaly': 1
    })

# 3. 60 AFTER_HOURS (22:00 - 06:00, > 5000)
for _ in range(ANOMALY_EACH):
    start_date = datetime(2024, 1, 1)
    dt = start_date + timedelta(days=random.randint(0, 360), hours=random.choice([22, 23, 0, 1, 2, 3, 4, 5]), minutes=random.randint(0, 59))
    amount = round(random.uniform(5000, 20000), 2)
    data.append({
        'id': str(uuid.uuid4()),
        'date': dt.isoformat(),
        'amount': amount,
        'currency': 'USD',
        'account_debit': random.choice(accounts),
        'account_credit': '1000-Banco',
        'description': "Mantenimiento urgente nocturno",
        'vendor_id': random.choice(normal_vendors),
        'employee_id': f"EMP_{random.randint(100, 999)}",
        'department': random.choice(departments),
        'source_system': 'csv',
        'is_anomaly': 1
    })

# 4. 60 VELOCITY_SPIKE (mismo vendor, mismo día, muchas trans)
spike_date = datetime(2024, 6, 15, 10, 0)
spike_vendor = "Vendor_SPIKE"
for i in range(ANOMALY_EACH):
    dt = spike_date + timedelta(minutes=i*2)
    amount = round(random.uniform(100, 500), 2)
    data.append({
        'id': str(uuid.uuid4()),
        'date': dt.isoformat(),
        'amount': amount,
        'currency': 'USD',
        'account_debit': random.choice(accounts),
        'account_credit': '1000-Banco',
        'description': f"Compra material oficina {i}",
        'vendor_id': spike_vendor,
        'employee_id': f"EMP_{random.randint(100, 999)}",
        'department': random.choice(departments),
        'source_system': 'csv',
        'is_anomaly': 1
    })

# 5. 60 SPLIT_TRANSACTION (mismo vendor, mismo dia, suma > 50k)
split_date = datetime(2024, 9, 20, 11, 0)
split_vendor = "Vendor_SPLIT"
for i in range(ANOMALY_EACH):
    dt = split_date + timedelta(minutes=i*15)
    amount = round(random.uniform(900, 1100), 2)
    data.append({
        'id': str(uuid.uuid4()),
        'date': dt.isoformat(),
        'amount': amount,
        'currency': 'USD',
        'account_debit': random.choice(accounts),
        'account_credit': '1000-Banco',
        'description': f"Factura parcial eq {i}",
        'vendor_id': split_vendor,
        'employee_id': f"EMP_{random.randint(100, 999)}",
        'department': random.choice(departments),
        'source_system': 'csv',
        'is_anomaly': 1
    })

# 6. 60 NEW_VENDOR_LARGE (vendor unico, > 30000)
for i in range(ANOMALY_EACH):
    dt = random_normal_date()
    amount = round(random.uniform(30000, 80000), 2)
    data.append({
        'id': str(uuid.uuid4()),
        'date': dt.isoformat(),
        'amount': amount,
        'currency': 'USD',
        'account_debit': random.choice(accounts),
        'account_credit': '1000-Banco',
        'description': "Adquisición nuevo software",
        'vendor_id': f"Vendor_NEW_{i}",
        'employee_id': f"EMP_{random.randint(100, 999)}",
        'department': random.choice(departments),
        'source_system': 'csv',
        'is_anomaly': 1
    })

df = pd.DataFrame(data)

# Asegurar orden aleatorio final pero manteniéndonos reproducibles
df = df.sample(frac=1, random_state=42).reset_index(drop=True)

# Crear directorio si no existe
os.makedirs(os.path.join(os.path.dirname(__file__), '.'), exist_ok=True)
output_path = os.path.join(os.path.dirname(__file__), 'sample_transactions.csv')
df.to_csv(output_path, index=False)

print(f"Dataset generado: {len(df)} filas, {df['is_anomaly'].sum()} anomalías")
