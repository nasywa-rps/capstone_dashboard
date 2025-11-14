import streamlit as st
from pymongo import MongoClient
import pandas as pd
import datetime
from datetime import timedelta
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Helmet Detection Dashboard | Analitik",
    layout="wide",
    page_icon="logo.png",
    initial_sidebar_state="collapsed"
)

# ===== LOGIN CHECK =====
# Check if user is logged in
if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.error("⚠️ Anda harus login terlebih dahulu!")
    st.info("👉 Silakan kembali ke halaman Home untuk login.")
    st.stop()

# Logout button in sidebar
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.username}")
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.switch_page("Home.py")

# ===== END LOGIN CHECK =====

# Custom CSS for compact layout
st.markdown("""
    <style>
    /* Compact layout - fit everything on one page */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        max-width: 100%;
    }
    
    .main {
        padding: 0rem 1rem;
    }
    
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .stMetric label {
        color: #31333F !important;
        font-size: 0.9rem !important;
    }
    
    .stMetric [data-testid="stMetricValue"] {
        color: #0e1117 !important;
        font-size: 1.5rem !important;
    }
    
    .stMetric [data-testid="stMetricDelta"] {
        color: #31333F !important;
        font-size: 0.85rem !important;
    }
    
    h1 {
        color: #1f77b4;
        padding-bottom: 10px;
        font-size: 1.8rem !important;
    }
    
    h2 {
        color: #2c3e50;
        padding-top: 5px;
        padding-bottom: 5px;
        font-size: 1.3rem !important;
    }
    
    /* Reduce spacing between elements */
    .element-container {
        margin-bottom: 0.5rem !important;
    }
    
    hr {
        margin: 0.5rem 0 !important;
    }
    </style>
""", unsafe_allow_html=True)


# Connect to database
try:
    client = MongoClient(st.secrets["COSMOSDB_CONN_STRING"])
    collection = client["image_database"]["image_metadata"]
    
    # Get stats
    total = collection.count_documents({})
    processed = collection.count_documents({"processed": True})
    
    # Support both old and new schema
    helmet = collection.count_documents({
        "$or": [
            {"helmet_status": "helmet"},
            {"helmet_status": "compliant"}
        ]
    })
    no_helmet = collection.count_documents({
        "$or": [
            {"helmet_status": "no_helmet"},
            {"helmet_status": "violation"}
        ]
    })
    
    # Calculate compliance rate
    compliance_rate = (helmet / processed * 100) if processed > 0 else 0
    violation_rate = (no_helmet / processed * 100) if processed > 0 else 0


    # === ROW 1: PIE CHART & GAUGE (COMPACT) ===
    st.subheader("📊 Analisis Kepatuhan")
    
    col_chart1, col_chart2 = st.columns([1, 1])
    
    with col_chart1:
        if processed > 0:
            # Compact Pie Chart
            fig_pie = go.Figure(data=[go.Pie(
                labels=['Patuh (Pakai Helm)', 'Melanggar (Tidak Pakai Helm)'],
                values=[helmet, no_helmet],
                hole=0.4,
                marker=dict(colors=['#2ecc71', '#e74c3c']),
                textinfo='label+percent',
                textfont=dict(size=11)
            )])
            
            fig_pie.update_layout(
                title=dict(text="Distribusi Kepatuhan", font=dict(size=14)),
                showlegend=True,
                height=250,  # Reduced from 350
                margin=dict(t=40, b=10, l=10, r=10),
                legend=dict(font=dict(size=10))
            )
            
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Belum ada data untuk ditampilkan")
    
    with col_chart2:
        if processed > 0:
            # Compact Gauge Chart
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=compliance_rate,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Tingkat Kepatuhan", 'font': {'size': 14}},
                number={'suffix': '%', 'font': {'size': 30}},
                gauge={
                    'axis': {'range': [None, 100], 'ticksuffix': '%', 'tickfont': {'size': 10}},
                    'bar': {'color': "#2ecc71" if compliance_rate >= 80 else "#f39c12" if compliance_rate >= 60 else "#e74c3c"},
                    'steps': [
                        {'range': [0, 60], 'color': "#ffe6e6"},
                        {'range': [60, 80], 'color': "#fff8e6"},
                        {'range': [80, 100], 'color': "#e6ffe6"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 3},
                        'thickness': 0.75,
                        'value': 80
                    }
                }
            ))
            
            fig_gauge.update_layout(
                height=250,  # Reduced from 350
                margin=dict(t=40, b=10, l=10, r=10)
            )
            
            st.plotly_chart(fig_gauge, use_container_width=True)
        else:
            st.info("Belum ada data untuk ditampilkan")
    
    st.markdown("---")
    
    # === ROW 2: TREND ANALYSIS (COMPACT) ===
    st.subheader("📈 Trend & Analisis Temporal")
    
    # Get all violators with timestamps
    violators = list(collection.find({
        "$or": [
            {"helmet_status": "no_helmet"},
            {"helmet_status": "violation"}
        ]
    }))
    
    if len(violators) > 0:
        df_violators = pd.DataFrame(violators)
        
        if 'processed_at' in df_violators.columns:
            df_violators['processed_at'] = pd.to_datetime(df_violators['processed_at'])
            df_violators['date'] = df_violators['processed_at'].dt.date
            df_violators['hour'] = df_violators['processed_at'].dt.hour
            
            col_trend1, col_trend2 = st.columns([2, 1])
            
            with col_trend1:
                # Compact Daily trend
                daily_violations = df_violators.groupby('date').size().reset_index(name='count')
                
                fig_trend = px.line(
                    daily_violations,
                    x='date',
                    y='count',
                    title='Trend Pelanggaran Harian',
                    labels={'date': 'Tanggal', 'count': 'Jumlah Pelanggar'},
                    markers=True
                )
                
                fig_trend.update_traces(
                    line=dict(color='#e74c3c', width=2),
                    marker=dict(size=6)
                )
                
                fig_trend.update_layout(
                    height=250,  # Reduced from 400
                    hovermode='x unified',
                    showlegend=False,
                    margin=dict(t=40, b=40, l=40, r=10),
                    title=dict(font=dict(size=14)),
                    xaxis=dict(title=dict(font=dict(size=11)), tickfont=dict(size=10)),
                    yaxis=dict(title=dict(font=dict(size=11)), tickfont=dict(size=10))
                )
                
                st.plotly_chart(fig_trend, use_container_width=True)
            
            with col_trend2:
                # Compact Hourly distribution
                hourly_violations = df_violators.groupby('hour').size().reset_index(name='count')
                
                fig_hour = px.bar(
                    hourly_violations,
                    x='hour',
                    y='count',
                    title='Distribusi per Jam',
                    labels={'hour': 'Jam', 'count': 'Jumlah'},
                    color='count',
                    color_continuous_scale='Reds'
                )
                
                fig_hour.update_layout(
                    height=250,  # Reduced from 400
                    showlegend=False,
                    xaxis=dict(tickmode='linear', dtick=3, title=dict(font=dict(size=11)), tickfont=dict(size=10)),
                    yaxis=dict(title=dict(font=dict(size=11)), tickfont=dict(size=10)),
                    margin=dict(t=40, b=40, l=40, r=10),
                    title=dict(font=dict(size=14))
                )
                
                st.plotly_chart(fig_hour, use_container_width=True)
        else:
            st.warning("Data timestamp tidak tersedia untuk analisis trend")
    else:
        st.info("Belum ada data pelanggaran")
    
    # === COMPACT FOOTER ===
    st.markdown("---")
    footer_col1, footer_col2 = st.columns([1, 1])
    with footer_col1:
        st.caption(f"🕐 Terakhir diperbarui: {datetime.datetime.now().strftime('%d %B %Y, %H:%M:%S')}")
    with footer_col2:
        st.caption("💾 Data source: Azure CosmosDB")


except Exception as e:
    st.error(f"⚠️ Terjadi kesalahan koneksi database: {str(e)}")
    st.info("Pastikan koneksi database tersedia dan credentials benar.")