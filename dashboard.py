import streamlit as st
from pymongo import MongoClient
import pandas as pd
import datetime
from datetime import timedelta
import plotly.express as px
import plotly.graph_objects as go

# Page config with custom theme
st.set_page_config(
    page_title="Helmet Detection Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stMetric:hover {
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        transition: 0.3s;
    }
    /* Fix metric text visibility */
    .stMetric label {
        color: #31333F !important;
    }
    .stMetric [data-testid="stMetricValue"] {
        color: #0e1117 !important;
    }
    .stMetric [data-testid="stMetricDelta"] {
        color: #31333F !important;
    }
    h1 {
        color: #1f77b4;
        padding-bottom: 20px;
    }
    h2 {
        color: #2c3e50;
        padding-top: 10px;
    }
    .dataframe {
        font-size: 14px;
    }
    div[data-testid="stHorizontalBlock"] {
        gap: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown("<h1 style='text-align: center;'>🪖 Dashboard Deteksi Helm Pengendara</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #7f8c8d; font-size: 16px;'>Monitoring Real-time Kepatuhan Helm Berkendara</p>", unsafe_allow_html=True)

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
    
    st.markdown("---")
    
    # === METRICS ROW WITH ENHANCED STYLING ===
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📊 Total Kendaraan", 
            value=f"{processed:,}",
            help="Total kendaraan yang telah diproses"
        )
    
    with col2:
        st.metric(
            label="✅ Memakai Helm", 
            value=f"{helmet:,}",
            delta=f"{compliance_rate:.1f}%",
            delta_color="normal"
        )
    
    with col3:
        st.metric(
            label="❌ Tidak Pakai Helm", 
            value=f"{no_helmet:,}",
            delta=f"{violation_rate:.1f}%",
            delta_color="inverse"
        )
    
    with col4:
        st.metric(
            label="🎯 Tingkat Kepatuhan", 
            value=f"{compliance_rate:.1f}%",
            help="Persentase pengendara yang memakai helm"
        )
    
    st.markdown("---")
    
    # === ROW 1: PIE CHART & GAUGE ===
    st.subheader("📊 Analisis Kepatuhan")
    
    col_chart1, col_chart2 = st.columns([1, 1])
    
    with col_chart1:
        if processed > 0:
            # Enhanced Pie Chart using Plotly
            fig_pie = go.Figure(data=[go.Pie(
                labels=['Patuh (Pakai Helm)', 'Melanggar (Tidak Pakai Helm)'],
                values=[helmet, no_helmet],
                hole=0.4,
                marker=dict(colors=['#2ecc71', '#e74c3c']),
                textinfo='label+percent',
                textfont=dict(size=14)
            )])
            
            fig_pie.update_layout(
                title="Distribusi Kepatuhan",
                showlegend=True,
                height=350,
                margin=dict(t=50, b=0, l=0, r=0)
            )
            
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Belum ada data untuk ditampilkan")
    
    with col_chart2:
        if processed > 0:
            # Gauge Chart for Compliance Rate
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=compliance_rate,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Tingkat Kepatuhan", 'font': {'size': 20}},
                delta={'reference': 80, 'suffix': '%'},
                gauge={
                    'axis': {'range': [None, 100], 'ticksuffix': '%'},
                    'bar': {'color': "#2ecc71" if compliance_rate >= 80 else "#f39c12" if compliance_rate >= 60 else "#e74c3c"},
                    'steps': [
                        {'range': [0, 60], 'color': "#ffe6e6"},
                        {'range': [60, 80], 'color': "#fff8e6"},
                        {'range': [80, 100], 'color': "#e6ffe6"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 80
                    }
                }
            ))
            
            fig_gauge.update_layout(
                height=350,
                margin=dict(t=50, b=0, l=20, r=20)
            )
            
            st.plotly_chart(fig_gauge, use_container_width=True)
            
            # Status indicator
            if compliance_rate >= 80:
                st.success("🎉 Status: SANGAT BAIK")
            elif compliance_rate >= 60:
                st.warning("⚠️ Status: CUKUP BAIK")
            else:
                st.error("🚨 Status: PERLU PERHATIAN")
        else:
            st.info("Belum ada data untuk ditampilkan")
    
    st.markdown("---")
    
    # === ROW 2: TREND ANALYSIS ===
    st.subheader("📈 Trend & Analisis Temporal")
    
    # Get all violators with timestamps - FIXED: Removed sort() from query
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
                # Daily trend
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
                    line=dict(color='#e74c3c', width=3),
                    marker=dict(size=8)
                )
                
                fig_trend.update_layout(
                    height=400,
                    hovermode='x unified',
                    showlegend=False
                )
                
                st.plotly_chart(fig_trend, use_container_width=True)
            
            with col_trend2:
                # Hourly distribution
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
                    height=400,
                    showlegend=False,
                    xaxis=dict(tickmode='linear', dtick=2)
                )
                
                st.plotly_chart(fig_hour, use_container_width=True)
        else:
            st.warning("Data timestamp tidak tersedia untuk analisis trend")
    else:
        st.info("Belum ada data pelanggaran")
    
    st.markdown("---")
    
    # === ROW 3: RECENT VIOLATIONS TABLE ===
    st.subheader("🚨 Daftar Pelanggar Terbaru")
    
    # FIXED: Get recent violators without sorting in query, sort in pandas instead
    recent_violators = list(collection.find({
        "$or": [
            {"helmet_status": "no_helmet"},
            {"helmet_status": "violation"}
        ]
    }).limit(100))
    
    if len(recent_violators) > 0:
        df_recent = pd.DataFrame(recent_violators)
        
        # Sort by processed_at if available
        if 'processed_at' in df_recent.columns:
            df_recent['processed_at'] = pd.to_datetime(df_recent['processed_at'])
            df_recent = df_recent.sort_values('processed_at', ascending=False).reset_index(drop=True)
        else:
            df_recent = df_recent.reset_index(drop=True)

        # Select and format columns
        columns_to_show = []
        if 'filename' in df_recent.columns:
            columns_to_show.append('filename')
        if 'url' in df_recent.columns:
            columns_to_show.append('url')
        if 'confidence' in df_recent.columns:
            df_recent['confidence'] = df_recent['confidence'].round(3)
            columns_to_show.append('confidence')
        if 'processed_at' in df_recent.columns:
            df_recent['processed_at_formatted'] = df_recent['processed_at'].dt.strftime('%Y-%m-%d %H:%M:%S')
            columns_to_show.append('processed_at_formatted')
        
        display_df = df_recent[columns_to_show].copy() if columns_to_show else df_recent.copy()
        display_df = display_df.rename(columns={
            'filename': 'Nama File',
            'url': 'URL Foto',
            'confidence': 'Confidence',
            'processed_at_formatted': 'Waktu Deteksi'
        })
        
        # Reset index again before adding 'No' column
        display_df = display_df.reset_index(drop=True)
        display_df.insert(0, 'No', range(1, len(display_df) + 1))
        
        st.dataframe(
            display_df,
            hide_index=True,
            use_container_width=True,
            height=400
        )
        
        # Download section
        col_dl1, col_dl2, col_dl3 = st.columns([1, 1, 2])
        
        with col_dl1:
            csv = display_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"pelanggar_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col_dl2:
            st.metric("Total Pelanggaran", f"{no_helmet:,}")
    else:
        st.success("✅ Tidak ada pelanggaran yang terdeteksi!")
    
    st.markdown("---")
    
    # === FOOTER ===
    footer_col1, footer_col2 = st.columns([1, 1])
    with footer_col1:
        st.caption(f"🕐 Terakhir diperbarui: {datetime.datetime.now().strftime('%d %B %Y, %H:%M:%S')}")
    with footer_col2:
        st.caption("💾 Data source: Azure CosmosDB")

except Exception as e:
    st.error(f"⚠️ Terjadi kesalahan koneksi database: {str(e)}")
    st.info("Pastikan koneksi database tersedia dan credentials benar.")