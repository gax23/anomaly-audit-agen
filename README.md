# Anomaly Audit Agent

## Descripción del Proyecto y Propuesta de Valor
Anomaly Audit Agent es un sistema avanzado impulsado por Inteligencia Artificial diseñado para auditar transacciones financieras y detectar anomalías en tiempo real. Se integra sin problemas con ERPs comunes para proporcionar análisis profundo y reportes de auditoría con explicabilidad (XAI).

Propuesta de valor: Reducir el fraude, asegurar el cumplimiento y automatizar la auditoría financiera con un alto grado de confianza y explicabilidad.

## Stack Tecnológico
- **Lenguaje**: Python 3.11+
- **Deep Learning / ML**: PyTorch (Autoencoder no supervisado) + scikit-learn (Isolation Forest, One-Class SVM)
- **Explicabilidad (XAI)**: SHAP (sitios waterfall png) + LIME (explicador secundario)
- **Base de Datos Temporal**: TimescaleDB (PostgreSQL con extensiones de series temporales / hypertables)
- **Caché y Alertas**: Redis
- **API Backend**: FastAPI con autenticación JWT y API Keys
- **Frontend Interactivo**: Streamlit (Dashboard interno)
- **Reportes PDF**: WeasyPrint + Jinja2 (Templates HTML/CSS)
- **Migraciones de BD**: Alembic
- **Testing & Infraestructura**: pytest, Docker, Docker Compose

## Arquitectura

```text
+-------------------+      +------------------+      +-------------------+
|                   |      |                  |      |                   |
|  ERPs (SAP, Odoo, +----->+  API (FastAPI)   +<-----+ Dashboard (UI)    |
|  Quickbooks, etc) |      |                  |      |                   |
+-------------------+      +--------+---------+      +-------------------+
                                    |
                                    v
                           +--------+---------+
                           |                  |
                           |  Motor ML / XAI  |
                           |                  |
                           +--------+---------+
                                    |
                  +-----------------+-----------------+
                  |                                   |
                  v                                   v
         +--------+---------+                +--------+---------+
         |                  |                |                  |
         |  TimescaleDB     |                |  Redis (Caché)   |
         |                  |                |                  |
         +------------------+                +------------------+
```

## Modelos de Detección
- **Autoencoder (PyTorch)**: Red neuronal profunda [input_dim → 64 → 32 → 16 → 32 → 64 → input_dim] entrenada no supervisadamente para minimizar el error de reconstrucción (MSE). Cuenta con aprendizaje incremental mediante el método `partial_fit()` que acumula muestras en un buffer antes de ajustar pesos.
- **Isolation Forest**: Algoritmo no paramétrico basado en árboles de aislamiento para identificar observaciones distantes en el espacio de características con soporte `warm_start`.
- **One-Class SVM**: Detector basado en hiperplanos no lineales para capturar fronteras complejas de densidad en los datos normales.
- **Ensemble Detector**: Combina ponderadamente los anomaly scores normalizados de los detectores individuales para elevar la precisión global y minimizar falsos positivos.

## Motor de Reglas de Negocio
Opera en paralelo con los modelos de IA evaluando 5 reglas deterministas clave:
- `ROUND_AMOUNT`: Monto exactamente redondo (ej. $10,000, $50,000) superior a un umbral configurable (señal clásica de fraude o bypass de aprobación).
- `AFTER_HOURS`: Transacciones ejecutadas en horario nocturno (22:00 a 06:00) de lunes a viernes o en fin de semana para montos significativos.
- `VELOCITY_SPIKE`: Más de N transacciones hacia el mismo proveedor registradas en una ventana corta de 1 hora.
- `SPLIT_TRANSACTION`: Múltiples pagos fraccionados en un mismo día hacia un mismo proveedor cuya suma supera el umbral diario de autorización ("smurfing").
- `NEW_VENDOR_LARGE`: Primer pago emitido a un proveedor de reciente creación cuyo monto supera el percentil 90 del historial.

## Ejemplo de Reporte de Anomalía

```text
⚠️ ANOMALÍA DETECTADA — Score: 0.87/1.0 (ALTA SEVERIDAD)

Transacción: TXN-2024-001234
Fecha: 15 de enero de 2024, 23:47
Monto: $47,500.00 USD
Cuenta débito: 5100-Gastos Operativos
Proveedor: XYZ Consulting S.A.

¿Por qué fue marcada?
• El monto supera en 4.2x el promedio histórico de este proveedor ($11,200)
• Ocurrió un domingo a las 23:47 (fuera del horario habitual de negocio)
• Detectamos 3 transacciones del mismo proveedor en las últimas 6 horas

Recomendación: Requiere revisión por el auditor responsable antes de aprobar.
```

## Performance y Seguridad
- **Latencia Máxima de Inferencia**: 200ms por transacción individual procesada en CPU sin GPU.
- **Batch Processing**: Procesa y analiza 10,000 transacciones en menos de 60 segundos.
- **Rendimiento de Dashboard**: El dashboard Streamlit se renderiza en menos de 3 segundos con 100,000 registros.
- **Encriptación en Reposo**: Cifrado transparente de datos sensibles (montos, cuentas, IDs) mediante SQLAlchemy `TypeDecorator`.
- **Seguridad de Secretos**: Configuración estricta mediante variables de entorno (sin credenciales ni claves API en código).

## Requisitos del Sistema
- Docker y Docker Compose
- Python 3.11+ (para desarrollo local)
- Al menos 4GB de RAM y 20GB de almacenamiento

## Instalación con Docker (Paso a Paso)

1. Clonar el repositorio:
   ```bash
   git clone https://github.com/tu-usuario/anomaly-audit-agent.git
   cd anomaly-audit-agent
   ```

2. Configurar las variables de entorno:
   ```bash
   cp .env.example .env
   # Edita el archivo .env con tus credenciales
   ```

3. Construir y levantar los contenedores:
   ```bash
   docker-compose up -d --build
   ```

4. Ejecutar las migraciones de base de datos (opcional si es automático):
   ```bash
   docker-compose exec api alembic upgrade head
   ```

## Configuración de Conectores ERP

Para habilitar la sincronización automática con ERPs, edita el archivo `.env` configurando las variables correspondientes:

| ERP | Variable de Entorno | Descripción |
|---|---|---|
| **SAP Business One** | `SAP_B1_SERVICE_LAYER_URL` | URL base del Service Layer REST API |
| | `SAP_B1_USERNAME` | Usuario de servicio SAP B1 |
| | `SAP_B1_PASSWORD` | Contraseña del usuario SAP B1 |
| | `SAP_B1_COMPANY_DB` | Nombre de la base de datos de la empresa |
| **QuickBooks Online** | `QB_CLIENT_ID` | OAuth2 Client ID |
| | `QB_CLIENT_SECRET` | OAuth2 Client Secret |
| | `QB_REFRESH_TOKEN` | OAuth2 Refresh Token |
| | `QB_REALM_ID` | Company Realm ID |
| **Odoo** | `ODOO_URL` | URL base de la instancia de Odoo |
| | `ODOO_DB` | Nombre de la base de datos Odoo |
| | `ODOO_API_KEY` | API Key de autenticación XML-RPC |
| | `ODOO_USERNAME` | Usuario con permisos de lectura contable |

## Endpoints de la API con Ejemplos cURL

### Autenticación
Obtener token de acceso:
```bash
curl -X POST "http://localhost:8000/api/v1/auth/token" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=admin&password=secret"
```

### Ingerir Transacciones (JSON)
```bash
curl -X POST "http://localhost:8000/api/v1/transactions/ingest" \
     -H "Authorization: Bearer <TU_TOKEN>" \
     -H "Content-Type: application/json" \
     -d '{"transactions": [{"date": "2024-01-15T10:00:00", "amount": 50000.0, "account_debit": "5100", "account_credit": "2100", "description": "Servicios"}]}'
```

### Ingerir Transacciones desde CSV (Multipart Upload)
```bash
curl -X POST "http://localhost:8000/api/v1/transactions/ingest/csv" \
     -H "Authorization: Bearer <TU_TOKEN>" \
     -F "file=@/ruta/a/sample_transactions.csv"
```

### Explicación de Anomalía (SHAP + Narrativa)
```bash
curl -X GET "http://localhost:8000/api/v1/anomalies/ANOMALY-1234/explain" \
     -H "Authorization: Bearer <TU_TOKEN>"
```

### Registrar Feedback de Auditor (TP / FP)
```bash
curl -X POST "http://localhost:8000/api/v1/anomalies/ANOMALY-1234/feedback" \
     -H "Authorization: Bearer <TU_TOKEN>" \
     -H "Content-Type: application/json" \
     -d '{"status": "TRUE_POSITIVE", "reviewer_id": "auditor_01", "notes": "Confirmado smurfing"}'
```

### Entrenamiento Incremental del Modelo
```bash
curl -X POST "http://localhost:8000/api/v1/model/train/incremental" \
     -H "Authorization: Bearer <TU_TOKEN>" \
     -H "Content-Type: application/json" \
     -d '{"transaction_ids": ["TXN-001", "TXN-002"]}'
```

### Consultar Estado del Modelo
```bash
curl -X GET "http://localhost:8000/api/v1/model/status" \
     -H "Authorization: Bearer <TU_TOKEN>"
```

### Generar Reporte PDF de Auditoría
```bash
curl -X GET "http://localhost:8000/api/v1/reports/generate?date_from=2024-01-01&date_to=2024-03-31" \
     -H "Authorization: Bearer <TU_TOKEN>" \
     --output reporte_auditoria.pdf
```

## Ejemplos de Uso
- **Auditoría Continua**: Configura una tarea programada para ingerir datos de tu ERP cada hora.
- **Auditoría Retrospectiva**: Sube un archivo CSV con transacciones del año pasado para un análisis completo.
- **Dashboard Interactivo**: Accede a `http://localhost:8501` para explorar los resultados.

## Estructura de Carpetas
```
anomaly-audit-agent/
├── README.md
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── pyproject.toml
│
├── config/
│   ├── settings.py          # Pydantic BaseSettings, variables de entorno
│   └── logging_config.py    # Logging estructurado JSON y enmascaramiento
│
├── connectors/              # Conectores a fuentes de datos ERP y archivos
│   ├── base.py              # Clase abstracta BaseConnector
│   ├── sap_b1.py            # Conector SAP Business One (REST API Service Layer)
│   ├── quickbooks.py        # Conector QuickBooks Online (OAuth2 SDK)
│   ├── odoo.py              # Conector Odoo (XML-RPC API Key)
│   └── csv_excel.py         # Ingesta genérica CSV/XLSX con validación de esquema
│
├── ingestion/               # Pipeline de normalización
│   ├── schema.py            # Pydantic models: Transaction, Account, JournalEntry
│   ├── normalizer.py        # Transforma datos de cualquier fuente al esquema unificado
│   └── pipeline.py          # Orquesta ingesta + normalización + almacenamiento
│
├── models/                  # Modelos de detección de anomalías
│   ├── base_detector.py     # Clase abstracta BaseDetector
│   ├── autoencoder.py       # Autoencoder PyTorch con entrenamiento incremental partial_fit()
│   ├── isolation_forest.py  # Isolation Forest con warm_start
│   ├── ensemble.py          # Ensemble que combina scores de múltiples detectores
│   └── trainer.py           # Lógica de entrenamiento y validación cruzada temporal
│
├── explainability/          # Capa de explicabilidad (XAI)
│   ├── shap_explainer.py    # SHAP values para cada anomalía detectada
│   ├── lime_explainer.py    # LIME como fallback o segunda opinión
│   └── narrative.py         # Genera texto explicativo en español
│
├── alerts/                  # Sistema de alertas y motor de reglas
│   ├── alert_model.py       # Pydantic model: Alert con severidad, score, explicación
│   ├── rules_engine.py      # Reglas de negocio deterministas (umbrales, listas negras)
│   └── notifier.py          # Email (SMTP) + webhook configurable
│
├── api/                     # FastAPI Backend API
│   ├── main.py              # Lifespan, CORS, middlewares
│   ├── auth.py              # JWT + API keys
│   ├── middleware.py        # Rate limiting, request logging, security headers
│   └── routes/
│       ├── transactions.py  # POST /ingest, POST /ingest/csv, GET /transactions
│       ├── anomalies.py     # GET /anomalies, GET /anomalies/{id}/explain, POST /feedback
│       ├── models.py        # POST /train, POST /train/incremental, GET /status
│       └── reports.py       # GET /reports/generate
│
├── dashboard/               # Streamlit Dashboard
│   └── app.py               # Dashboard con filtros por fecha, cuenta, severidad
│
├── reports/                 # Generación de reportes PDF
│   ├── generator.py         # Orquesta generación de PDF con WeasyPrint
│   └── templates/
│       └── audit_report.html # Template Jinja2 para reporte de auditoría con firmas
│
├── database/                # Base de datos y ORM
│   ├── connection.py        # Conexión AsyncEngine y AsyncSessionLocal
│   ├── models.py            # SQLAlchemy ORM models con TypeDecorator encriptado
│   ├── migrations/          # Alembic migrations (TimescaleDB hypertable)
│   └── repositories/        # Repository pattern (TransactionRepository, AnomalyRepository)
│
└── tests/                   # Suite de Pruebas Automated
    ├── unit/                # Tests unitarios (autoencoder, rules_engine, normalizer)
    ├── integration/         # Tests de integración (csv_connector, pipeline_e2e, api_endpoints)
    └── fixtures/
        ├── generate_dataset.py       # Generador del dataset sintético
        └── sample_transactions.csv   # Dataset sintético de 10,000 transacciones
```

## Licencia MIT

Copyright (c) 2026 Anomaly Audit Agent

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
