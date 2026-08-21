"""TrendClimber — detecta en qué fase está una tendencia antes de que se masifique."""

import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from src.keyword_generator import LIFECYCLE_STAGES, generate_keywords
from src.lifecycle_classifier import STAGE_COLORS, STAGE_DESCRIPTIONS, classify_lifecycle
from src.trends_fetcher import fetch_multi_window_curves

load_dotenv()

st.set_page_config(
    page_title="TrendClimber",
    page_icon="📈",
    layout="wide",
)

# --- Styles ---
st.markdown(
    """
    <style>
    .stage-badge {
        display: inline-block;
        padding: 0.4rem 1rem;
        border-radius: 999px;
        font-weight: 700;
        font-size: 1.1rem;
        color: white;
        margin-bottom: 0.5rem;
    }
    .metric-card {
        background: #f8fafc;
        border-radius: 12px;
        padding: 1rem;
        border: 1px solid #e2e8f0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Sidebar ---
with st.sidebar:
    st.title("⚙️ Configuración")
    geo = st.selectbox(
        "Región",
        options=["ES", "AR", "MX", ""],
        format_func=lambda x: {"ES": "🇪🇸 España", "AR": "🇦🇷 Argentina", "MX": "🇲🇽 México", "": "🌍 Global"}[x],
    )
    if not os.getenv("GOOGLE_API_KEY"):
        st.warning("Configura `GOOGLE_API_KEY` en un archivo `.env` para usar Gemini.")

    st.caption("Curvas: último año, 30 días y 7 días (hasta ayer)")

    st.divider()
    st.markdown("**Fases del ciclo de vida**")
    for stage in LIFECYCLE_STAGES:
        color = STAGE_COLORS[stage]
        st.markdown(
            f'<span style="color:{color};font-weight:600;">●</span> {stage}',
            unsafe_allow_html=True,
        )

# --- Main ---
st.title("📈 TrendClimber")
st.markdown(
    "Detecta **en qué fase** está una tendencia antes de que se masifique. "
    "Las marcas suelen llegar tarde — cuando ya está saturada."
)

col1, col2 = st.columns([1, 1])
with col1:
    title = st.text_input("Título de la tendencia", placeholder="Ej: Quiet Luxury")
with col2:
    description = st.text_area(
        "Descripción",
        placeholder="Describe el fenómeno, contexto cultural, audiencia...",
        height=100,
    )

analyze = st.button("🔍 Analizar tendencia", type="primary", use_container_width=True)

if analyze:
    if not title.strip():
        st.error("Ingresa un título para la tendencia.")
        st.stop()
    if not description.strip():
        st.error("Ingresa una descripción de la tendencia.")
        st.stop()
    if not os.getenv("GOOGLE_API_KEY"):
        st.error("Falta `GOOGLE_API_KEY`. Copia `.env.example` a `.env` y agrega tu clave.")
        st.stop()

    with st.spinner("Generando keywords con Gemini..."):
        try:
            keywords, reasoning = generate_keywords(title, description, geo=geo)
        except Exception as e:
            st.error(f"Error al generar keywords: {e}")
            st.stop()

    st.success(f"**Keywords detectadas:** {', '.join(keywords)}")
    st.info(f"💡 {reasoning}")

    with st.spinner("Consultando Google Trends..."):
        try:
            timeline, classify_data, data_until, _series = fetch_multi_window_curves(
                keywords, geo=geo
            )
        except Exception as e:
            st.error(f"Error al obtener datos de Trends: {e}")
            st.stop()

    with st.spinner("Clasificando ciclo de vida..."):
        result = classify_lifecycle(classify_data)

    color = STAGE_COLORS[result.stage]
    st.markdown(
        f'<div class="stage-badge" style="background:{color};">{result.stage}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(f"**Confianza:** {result.confidence * 100:.0f}%")
    st.markdown(result.description)

    # Metrics row
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Interés promedio", result.metrics["avg_interest"])
    m2.metric("Interés reciente", result.metrics["avg_recent"])
    m3.metric("Ratio crecimiento", f"{result.metrics['growth_ratio']}x")
    m4.metric("Días analizados", result.metrics["days_analyzed"])

    # Chart — suma de todas las keywords
    st.subheader("Curva de búsqueda")
    st.caption(f"Datos hasta ayer ({data_until})")
    chart_df = pd.DataFrame(timeline)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=chart_df["date"],
            y=chart_df["year"],
            mode="lines",
            name="Último año",
            line=dict(width=2.5, color="#4f24ee"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=chart_df["date"],
            y=chart_df["days30"],
            mode="lines",
            name="Últimos 30 días",
            line=dict(width=2.5, color="#f97316"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=chart_df["date"],
            y=chart_df["days7"],
            mode="lines",
            name="Últimos 7 días",
            line=dict(width=3, color="#22c55e"),
        )
    )
    fig.update_layout(
        xaxis_title="Fecha",
        yaxis_title="Interés total (suma keywords)",
        hovermode="x unified",
        height=420,
        margin=dict(l=0, r=0, t=30, b=0),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Stage scores
    with st.expander("Ver puntuación por fase"):
        score_df = pd.DataFrame(
            [{"Fase": k, "Score": v} for k, v in result.stage_scores.items()]
        ).sort_values("Score", ascending=True)
        st.bar_chart(score_df.set_index("Fase"))

    # Raw data + export
    with st.expander("Datos crudos"):
        st.dataframe(chart_df, use_container_width=True)
        csv = chart_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Descargar CSV",
            data=csv,
            file_name=f"trend_{title.replace(' ', '_').lower()}.csv",
            mime="text/csv",
        )

else:
    st.divider()
    st.subheader("¿Cómo funciona?")
    steps = st.columns(3)
    steps[0].markdown("**1. Describe la tendencia**\n\nTítulo + contexto cultural.")
    steps[1].markdown("**2. IA genera keywords**\n\nGemini propone términos de búsqueda reales.")
    steps[2].markdown("**3. Clasificación automática**\n\nGoogle Trends + análisis de curva.")

    st.markdown("---")
    for stage in LIFECYCLE_STAGES:
        c = STAGE_COLORS[stage]
        st.markdown(
            f'<span style="color:{c};font-weight:700;">{stage}</span> — '
            f'{STAGE_DESCRIPTIONS[stage]}',
            unsafe_allow_html=True,
        )
