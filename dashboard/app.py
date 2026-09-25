"""
Dashboard Streamlit para monitoreo de anomalías financieras en tiempo real.
Muestra KPIs, tabla filtrable de anomalías, serie temporal y detalle con explicación.

Ejecutar con: streamlit run dashboard/app.py
"""
import sys
from pathlib import Path

# Añadir la raíz del proyecto al path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import streamlit as st
import requests
from datetime import datetime, date, timedelta
from typing import Optional

# ─── Configuración de página ───────────────────────────────────────────────────
st.set_page_config(
    page_title="Agente de Auditoría Financiera",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Estilos CSS personalizados ────────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d6a4f 100%);
        padding: 1rem;
        border-radius: 8px;
        color: white;
        text-align: center;
    }
    .severity-HIGH { color: #ff4444; font-weight: bold; }
    .severity-MEDIUM { color: #ff8800; font-weight: bold; }
    .severity-LOW { color: #ffcc00; }
    .severity-CRITICAL { color: #cc0000; font-weight: bold; font-size: 1.1em; }
    .stDataFrame { font-size: 0.85em; }
</style>
""", unsafe_allow_html=True)

# ─── Configuración de API ───────────────────────────────────────────────────────
API_BASE = "http://localhost:8000/api/v1"
API_KEY = "demo-api-key"  # En producción: desde st.secrets o variable de entorno
HEADERS = {"X-API-Key": API_KEY}


@st.cache_data(ttl=30)
def fetch_anomalies(date_from: str, date_to: str, severity: Optional[str],
                    status: Optional[str], page: int = 1) -> dict:
    """Obtiene anomalías de la API con caché de 30 segundos."""
    params = {"date_from": date_from, "date_to": date_to, "page": page, "page_size": 200}
    if severity:
        params["severity"] = severity
    if status:
        params["status"] = status
    try:
        resp = requests.get(f"{API_BASE}/anomalies", params=params, headers=HEADERS, timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {"total": 0, "data": [], "pages": 0}


@st.cache_data(ttl=60)
def fetch_model_status() -> dict:
    """Obtiene el estado del modelo ML."""
    try:
        resp = requests.get(f"{API_BASE}/model/status", headers=HEADERS, timeout=3)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {"status": "DESCONECTADO", "model_version": 0, "last_trained_at": None}


def load_sample_data() -> pd.DataFrame:
    """Carga datos de muestra del CSV de fixtures para demo sin API."""
    csv_path = Path(__file__).parent.parent / "tests" / "fixtures" / "sample_transactions.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path, parse_dates=["date"])
        # Simular columnas de anomalías para el demo
        anomalies = df[df["is_anomaly"] == 1].copy()
        anomalies["anomaly_score"] = np.random.uniform(0.6, 0.99, len(anomalies))
        anomalies["severity"] = pd.cut(
            anomalies["anomaly_score"],
            bins=[0, 0.6, 0.75, 0.9, 1.0],
            labels=["LOW", "MEDIUM", "HIGH", "CRITICAL"],
        )
        anomalies["status"] = "OPEN"
        anomalies["detected_at"] = anomalies["date"]
        return anomalies
    return pd.DataFrame()


# ─── Sidebar: Filtros ──────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/color/96/financial-analytics.png", width=60)
    st.title("🔍 Auditoría IA")
    st.markdown("---")

    st.subheader("📅 Período")
    col1, col2 = st.columns(2)
    with col1:
        date_from = st.date_input("Desde", value=date.today() - timedelta(days=90))
    with col2:
        date_to = st.date_input("Hasta", value=date.today())

    st.subheader("🎯 Filtros")
    severity_filter = st.selectbox(
        "Severidad",
        options=["Todas", "CRITICAL", "HIGH", "MEDIUM", "LOW"],
        index=0,
    )
    status_filter = st.selectbox(
        "Estado",
        options=["Todos", "OPEN", "TRUE_POSITIVE", "FALSE_POSITIVE", "UNDER_REVIEW"],
        index=0,
    )

    st.markdown("---")
    use_demo = st.checkbox("🎭 Modo Demo (sin API)", value=True,
                           help="Usa el dataset de fixtures en lugar de la API")

    if st.button("🔄 Actualizar datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ─── Carga de datos ────────────────────────────────────────────────────────────
severity_param = None if severity_filter == "Todas" else severity_filter
status_param = None if status_filter == "Todos" else status_filter

if use_demo:
    df_anomalies = load_sample_data()
    if not df_anomalies.empty:
        if severity_param:
            df_anomalies = df_anomalies[df_anomalies["severity"] == severity_param]
        if date_from and date_to:
            df_anomalies = df_anomalies[
                (df_anomalies["date"].dt.date >= date_from) &
                (df_anomalies["date"].dt.date <= date_to)
            ]
    total_anomalies = len(df_anomalies)
    api_data = {"total": total_anomalies, "data": df_anomalies.to_dict("records")}
else:
    api_data = fetch_anomalies(
        str(date_from), str(date_to), severity_param, status_param
    )
    df_anomalies = pd.DataFrame(api_data.get("data", []))
    total_anomalies = api_data.get("total", 0)

# ─── Header ───────────────────────────────────────────────────────────────────
st.title("🏦 Agente de Detección de Anomalías Financieras")
st.caption(f"Período: {date_from} → {date_to} | Actualización cada 30s")

# ─── KPIs principales ─────────────────────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)

if not df_anomalies.empty and "severity" in df_anomalies.columns:
    n_critical = len(df_anomalies[df_anomalies["severity"] == "CRITICAL"])
    n_high = len(df_anomalies[df_anomalies["severity"] == "HIGH"])
    n_open = len(df_anomalies[df_anomalies.get("status", "OPEN") == "OPEN"]) if "status" in df_anomalies.columns else total_anomalies
    avg_score = df_anomalies["anomaly_score"].mean() if "anomaly_score" in df_anomalies.columns else 0
else:
    n_critical, n_high, n_open, avg_score = 0, 0, 0, 0

col1.metric("⚠️ Total Anomalías", total_anomalies)
col2.metric("🔴 Críticas", n_critical, delta=None)
col3.metric("🟠 Alta Severidad", n_high)
col4.metric("📂 Abiertas", n_open)
col5.metric("📊 Score Promedio", f"{avg_score:.3f}" if avg_score else "N/A")

st.markdown("---")

# ─── Gráficos ─────────────────────────────────────────────────────────────────
if not df_anomalies.empty and "date" in df_anomalies.columns:
    col_chart1, col_chart2 = st.columns([2, 1])

    with col_chart1:
        st.subheader("📈 Anomalías por día")
        df_anomalies["date"] = pd.to_datetime(df_anomalies["date"])
        daily = df_anomalies.groupby(df_anomalies["date"].dt.date).size().reset_index()
        daily.columns = ["Fecha", "Anomalías"]
        st.line_chart(daily.set_index("Fecha"))

    with col_chart2:
        st.subheader("🎯 Distribución por severidad")
        if "severity" in df_anomalies.columns:
            sev_counts = df_anomalies["severity"].value_counts()
            st.bar_chart(sev_counts)

# ─── Tabla de anomalías ────────────────────────────────────────────────────────
st.subheader(f"📋 Anomalías detectadas ({total_anomalies} total)")

if not df_anomalies.empty:
    display_cols = [c for c in ["date", "amount", "vendor_id", "department",
                                "severity", "anomaly_score", "status", "is_anomaly"]
                    if c in df_anomalies.columns]

    df_display = df_anomalies[display_cols].copy()
    if "anomaly_score" in df_display.columns:
        df_display["anomaly_score"] = df_display["anomaly_score"].round(4)

    st.dataframe(
        df_display,
        use_container_width=True,
        height=400,
        column_config={
            "date": st.column_config.DatetimeColumn("Fecha", format="DD/MM/YYYY HH:mm"),
            "amount": st.column_config.NumberColumn("Monto", format=r"\$%.2f"),
            "anomaly_score": st.column_config.ProgressColumn(
                "Score", min_value=0, max_value=1, format="%.3f"
            ),
            "severity": st.column_config.TextColumn("Severidad"),
            "status": st.column_config.TextColumn("Estado"),
        },
    )
else:
    st.info("No se encontraron anomalías para el período y filtros seleccionados.")

# ─── Detalle de anomalía seleccionada ─────────────────────────────────────────
st.markdown("---")
st.subheader("🔎 Detalle y Explicación")

if not use_demo:
    anomaly_id = st.text_input("ID de anomalía a examinar:")
    if anomaly_id and st.button("Ver explicación"):
        try:
            resp = requests.get(
                f"{API_BASE}/anomalies/{anomaly_id}/explain",
                headers=HEADERS, timeout=5
            )
            if resp.status_code == 200:
                data = resp.json()
                st.markdown(f"**Score:** {data.get('anomaly_score', 0):.3f}")
                st.markdown(f"**Severidad:** {data.get('severity', 'N/A')}")
                st.markdown("**Narrativa:**")
                st.code(data.get("narrative", "No disponible"), language=None)
                if data.get("shap_values"):
                    st.json(data["shap_values"])
            else:
                st.error(f"Error {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            st.error(f"No se pudo conectar a la API: {e}")
else:
    if not df_anomalies.empty and "vendor_id" in df_anomalies.columns:
        selected = st.selectbox(
            "Selecciona una transacción del demo:",
            options=df_anomalies["vendor_id"].dropna().unique()[:20],
        )
        row = df_anomalies[df_anomalies["vendor_id"] == selected].iloc[0]
        score = row.get("anomaly_score", 0.75)
        sev = row.get("severity", "HIGH")
        st.markdown(f"""
**⚠️ ANOMALÍA DETECTADA — Score: {score:.2f}/1.0 ({sev} SEVERIDAD)**

- **Fecha:** {row['date']}
- **Monto:** \u0024{row.get('amount', 0):,.2f}
- **Proveedor:** {row.get('vendor_id', 'N/A')}
- **Departamento:** {row.get('department', 'N/A')}

**¿Por qué fue marcada?**
- El monto supera el umbral de detección para este proveedor
- Patrón de transacción inusual detectado por el modelo autoencoder

*Conéctese a la API para ver explicaciones SHAP completas*
        """)

# ─── Footer ───────────────────────────────────────────────────────────────────
st.markdown("---")
model_status = fetch_model_status() if not use_demo else {"status": "DEMO"}
st.caption(
    f"🤖 Modelo: {model_status.get('status', 'N/A')} | "
    f"Versión: {model_status.get('model_version', 0)} | "
    f"Entrenado: {model_status.get('last_trained_at', 'N/A')}"
)
