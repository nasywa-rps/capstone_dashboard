import streamlit as st
from pymongo import MongoClient
import pandas as pd
import datetime
from datetime import timedelta
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image
import hashlib

# Page config with custom theme
st.set_page_config(
    page_title="Helmet Detection Dashboard",
    layout="wide",
    page_icon="logo.png",
    initial_sidebar_state="collapsed"
)

# ===== LOGIN SYSTEM =====
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Users dictionary (you can also move this to secrets.toml)
USERS = {
    "admin": hash_password("admin123"),
    "user": hash_password("user123"),
}

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None

def logout():
    st.session_state.logged_in = False
    st.session_state.username = None
    st.rerun()

def login(username, password):
    hashed_pw = hash_password(password)
    if username in USERS and USERS[username] == hashed_pw:
        st.session_state.logged_in = True
        st.session_state.username = username
        return True
    return False

# ===== LOGIN PAGE =====
if not st.session_state.logged_in:
    st.markdown("""
        <style>
        .block-container {
            padding-top: 3rem !important;
            max-width: 450px !important;
        }
        .login-box {
            background-color: #f8f9fa;
            padding: 1.5rem;
            border-radius: 15px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-bottom: 1rem;
        }
        .stButton>button {
            width: 100%;
            background-color: #1f77b4;
            color: white;
            font-weight: 600;
            padding: 0.5rem;
            border-radius: 8px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Logo
    try:
        logo = Image.open("logo.png")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(logo, use_container_width=True)
    except:
        pass
    
    st.markdown("<h1 style='text-align: center; color: #1f77b4;'>🔐 Login Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #7f8c8d; margin-bottom: 2rem;'>SCOPE: Safety and Compliance Observation for Protection Equipment</p>", unsafe_allow_html=True)
    
    # Removed the login-box div wrapper
    
    with st.form("login_form"):
        username = st.text_input("👤 Username", placeholder="Masukkan username")
        password = st.text_input("🔑 Password", type="password", placeholder="Masukkan password")
        submit = st.form_submit_button("🚀 Login")
        
        if submit:
            if username and password:
                if login(username, password):
                    st.success("✅ Login berhasil!")
                    st.rerun()
                else:
                    st.error("❌ Username atau password salah!")
            else:
                st.warning("⚠️ Mohon isi username dan password!")
    
    st.markdown("---")
    st.info("**Demo:** Username: `admin` / Password: `admin123`")
    
    st.stop()  # Stop execution here if not logged in

# ===== MAIN DASHBOARD (Only shown after login) =====

# Custom CSS
st.markdown("""
    <style>
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }
    
    .main {
        padding: 0rem 1rem;
    }
    
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
    }
    
    .stMetric label {
        color: #31333F !important;
    }
    
    .stMetric [data-testid="stMetricValue"] {
        color: #0e1117 !important;
    }
    
    .stMetric [data-testid="stMetricDelta"] {
        color: #31333F !important;
    }
    
    .dataframe {
        font-size: 13px;
    }
    
    h1 {
        color: #1f77b4;
        padding-bottom: 10px;
    }
    
    h2 {
        color: #2c3e50;
        padding-top: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# Logout button in sidebar
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.username}")
    if st.button("🚪 Logout", use_container_width=True):
        logout()

# === LOGO AND HEADER ===
try:
    logo = Image.open("logo.png")
    col_empty1, col_content, col_empty2 = st.columns([1, 4, 1])
    
    with col_content:
        col_logo_small, col_title_small = st.columns([1, 6])
        
        with col_logo_small:
            st.markdown("<div style='padding-top: 5px;'></div>", unsafe_allow_html=True)
            st.image(logo, use_container_width=True)
        
        with col_title_small:
            st.markdown("<h1 style='margin-top: 15px; text-align: center;'>Selamat Datang di Dashboard</h1>", unsafe_allow_html=True)
            st.markdown("<p style='color: #7f8c8d; font-size: 16px; margin-top: -10px; text-align: center;'>SCOPE : Safety and Compliance Observation for Protection Equipment</p>", unsafe_allow_html=True)

except FileNotFoundError:
    st.markdown("<h1 style='text-align: center;'>Selamat Datang di Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #7f8c8d; font-size: 16px;'>SCOPE : Safety and Compliance Observation for Protection Equipment</p>", unsafe_allow_html=True)
except Exception as e:
    st.error(f"Error loading logo: {str(e)}")

# ===== DATABASE CONNECTION =====
@st.cache_resource
def init_connection():
    """Initialize MongoDB connection (cached across reruns)"""
    return MongoClient(st.secrets["COSMOSDB_CONN_STRING"])

@st.cache_data(ttl=60)
def get_database_stats():
    """Fetch all statistics in a single optimized query"""
    client = init_connection()
    collection = client["image_database"]["image_metadata"]
    
    pipeline = [
        {
            "$facet": {
                "total": [{"$count": "count"}],
                "processed": [
                    {"$match": {"processed": True}},
                    {"$count": "count"}
                ],
                "helmet": [
                    {"$match": {
                        "processed": True,
                        "helmet_status": {"$in": ["helmet", "compliant"]}
                    }},
                    {"$count": "count"}
                ],
                "no_helmet": [
                    {"$match": {
                        "processed": True,
                        "helmet_status": {"$in": ["no_helmet", "violation"]}
                    }},
                    {"$count": "count"}
                ]
            }
        }
    ]
    
    result = list(collection.aggregate(pipeline))[0]
    
    return {
        'total': result['total'][0]['count'] if result['total'] else 0,
        'processed': result['processed'][0]['count'] if result['processed'] else 0,
        'helmet': result['helmet'][0]['count'] if result['helmet'] else 0,
        'no_helmet': result['no_helmet'][0]['count'] if result['no_helmet'] else 0
    }

@st.cache_data(ttl=60)
def get_recent_records():
    """Fetch 10 most recent records regardless of status"""
    client = init_connection()
    collection = client["image_database"]["image_metadata"]
    
    recent_records = list(collection.find({}).limit(50))
    
    records_sorted = sorted(
        recent_records, 
        key=lambda x: x.get('uploaded_at', datetime.datetime.min),
        reverse=True
    )
    
    return records_sorted[:10]

# ===== MAIN DASHBOARD =====
try:
    with st.spinner('Memuat data...'):
        stats = get_database_stats()
    
    total = stats['total']
    processed = stats['processed']
    helmet = stats['helmet']
    no_helmet = stats['no_helmet']
    
    compliance_rate = (helmet / processed * 100) if processed > 0 else 0
    violation_rate = (no_helmet / processed * 100) if processed > 0 else 0
    
    st.markdown("---")
    
    # === METRICS ROW ===
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
    
    # === RECENT RECORDS TABLE ===
    st.subheader("🕒 10 Data Terbaru")
    
    recent_records = get_recent_records()
    
    if len(recent_records) > 0:
        df_recent = pd.DataFrame(recent_records)
        
        df_recent['No'] = range(1, len(df_recent) + 1)
        
        if 'uploaded_at' in df_recent.columns:
            df_recent['Tanggal'] = pd.to_datetime(df_recent['uploaded_at']).dt.strftime('%Y-%m-%d')
            df_recent['Waktu'] = pd.to_datetime(df_recent['uploaded_at']).dt.strftime('%H:%M:%S')
        else:
            df_recent['Tanggal'] = 'N/A'
            df_recent['Waktu'] = 'N/A'
        
        df_recent['Status'] = df_recent['helmet_status'].apply(
            lambda x: 'Patuh ✅' if x in ['helmet', 'compliant'] else 'Melanggar ❌'
        )
        
        display_df = df_recent[['No', 'Tanggal', 'Waktu', 'filename', 'Status']].copy()
        display_df.columns = ['No', 'Tanggal', 'Waktu', 'Nama File', 'Status']
        
        st.dataframe(
            display_df,
            hide_index=True,
            use_container_width=True,
            height=400
        )
        
        col_dl1, col_dl2, col_dl3 = st.columns([1, 1, 2])
        
        with col_dl1:
            csv = display_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"10_data_terbaru_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col_dl2:
            st.metric("Total Data", f"{len(recent_records)}")
    else:
        st.info("ℹ️ Tidak ada data yang tersedia")

except Exception as e:
    st.error(f"⚠️ Terjadi kesalahan koneksi database: {str(e)}")
    st.info("Pastikan koneksi database tersedia dan credentials benar.")