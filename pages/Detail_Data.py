import streamlit as st
from pymongo import MongoClient
import pandas as pd
import datetime
from PIL import Image
from io import BytesIO
from azure.storage.blob import BlobServiceClient

st.set_page_config(
    page_title="Helmet Detection Dashboard | Detail Data",
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

# Custom CSS for layout
st.markdown("""
    <style>
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }
    
    .main {
        padding: 0rem 1rem;
    }
    
    /* Table styling */
    .dataframe {
        font-size: 13px;
    }
    
    /* Detail panel styling */
    .detail-panel {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        border: 2px solid #dee2e6;
        height: 100%;
    }
    
    .detail-label {
        font-weight: 600;
        color: #495057;
        margin-top: 10px;
    }
    
    .detail-value {
        color: #212529;
        margin-bottom: 8px;
    }
    
    /* Status badges */
    .status-compliant {
        background-color: #d4edda;
        color: #155724;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: 600;
    }
    
    .status-violation {
        background-color: #f8d7da;
        color: #721c24;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: 600;
    }
    
    h1 {
        color: #1f77b4;
        font-size: 2rem !important;
        margin-bottom: 1rem;
    }
    
    h2 {
        color: #2c3e50;
        font-size: 1.3rem !important;
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)


# Title
st.title("📋 Detail Data Deteksi Helm")


# ===== DATABASE CONNECTION =====
@st.cache_resource
def init_connection():
    return MongoClient(st.secrets["COSMOSDB_CONN_STRING"])


@st.cache_resource
def init_blob_client():
    """Initialize Azure Blob Storage client with authentication"""
    return BlobServiceClient.from_connection_string(
        st.secrets["AZURE_STORAGE_CONNECTION_STRING"]
    )


@st.cache_data(ttl=30)
def get_all_records(status_filter="Semua", date_filter=None):
    """Fetch all records with filters"""
    client = init_connection()
    collection = client["image_database"]["image_metadata"]
    
    # Build query
    query = {}
    
    # Status filter
    if status_filter == "Patuh (Pakai Helm)":
        query["helmet_status"] = {"$in": ["helmet", "compliant"]}
    elif status_filter == "Melanggar (Tidak Pakai Helm)":
        query["helmet_status"] = {"$in": ["no_helmet", "violation"]}
    
    # Date filter
    if date_filter:
        start_date = datetime.datetime.combine(date_filter, datetime.time.min)
        end_date = datetime.datetime.combine(date_filter, datetime.time.max)
        query["uploaded_at"] = {"$gte": start_date, "$lte": end_date}
    
    # Fetch data WITHOUT sorting (CosmosDB requires index for sort)
    records = list(collection.find(query).limit(500))
    
    # Sort in Python by uploaded_at
    records_sorted = sorted(
        records, 
        key=lambda x: x.get('uploaded_at', datetime.datetime.min),
        reverse=True
    )
    
    return records_sorted


def load_image_from_blob(blob_url):
    """Load image from Azure Blob Storage with authentication"""
    try:
        # Get blob client
        blob_service_client = init_blob_client()
        
        # Extract container and blob name from URL
        # Example URL: https://storagetugas.blob.core.windows.net/photo/photo_20251113_171531_427061.jpg
        parts = blob_url.split('/')
        container_name = parts[-2]  # 'photo'
        blob_name = parts[-1]        # 'photo_20251113_171531_427061.jpg'
        
        # Get blob client for specific blob
        blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_name
        )
        
        # Download blob data
        blob_data = blob_client.download_blob().readall()
        
        # Convert to PIL Image
        img = Image.open(BytesIO(blob_data))
        return img
    except Exception as e:
        st.error(f"Error loading image: {str(e)}")
        return None


# ===== FILTERS =====
with st.expander("🔍 Filter Data", expanded=True):
  col_filter1, col_filter2, col_filter3 = st.columns([2, 2, 1])

with col_filter1:
    status_filter = st.selectbox(
        "Status Kepatuhan",
        ["Semua", "Patuh (Pakai Helm)", "Melanggar (Tidak Pakai Helm)"],
        index=0
    )

with col_filter2:
    date_filter = st.date_input(
        "Filter Tanggal",
        value=None,
        help="Kosongkan untuk melihat semua tanggal"
    )

with col_filter3:
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.markdown("---")


# ===== MAIN LAYOUT: TABLE (3/4) + DETAIL PANEL (1/4) =====
try:
    # Fetch data
    records = get_all_records(
        status_filter=status_filter,
        date_filter=date_filter if date_filter else None
    )
    
    if len(records) > 0:
        # Convert to DataFrame
        df = pd.DataFrame(records)
        
        # Prepare display columns
        df['No'] = range(1, len(df) + 1)
        
        # Format datetime
        if 'uploaded_at' in df.columns:
            df['Tanggal'] = pd.to_datetime(df['uploaded_at']).dt.strftime('%Y-%m-%d')
            df['Waktu'] = pd.to_datetime(df['uploaded_at']).dt.strftime('%H:%M:%S')
        else:
            df['Tanggal'] = 'N/A'
            df['Waktu'] = 'N/A'
        
        # Status mapping
        df['Status'] = df['helmet_status'].apply(
            lambda x: 'Patuh ✅' if x in ['helmet', 'compliant'] else 'Melanggar ❌'
        )
        
        # Format confidence rate (as percentage)
        if 'confidence' in df.columns:
            df['Confidence'] = df['confidence'].apply(
                lambda x: f"{x*100:.1f}%" if pd.notna(x) else 'N/A'
            )
        else:
            df['Confidence'] = 'N/A'
        
        # Display columns with confidence
        display_df = df[['No', 'Tanggal', 'Waktu', 'filename', 'Confidence', 'Status']].copy()
        display_df.columns = ['No', 'Tanggal', 'Waktu', 'Nama File', 'Confidence', 'Status']
        
        # Create two columns: Table (3/4) and Detail Panel (1/4)
        col_table, col_detail = st.columns([3, 1])
        
        with col_table:
            st.subheader(f"📊 Data Kendaraan ({len(records)} data)")
            
            # Display table with selection
            selected_indices = st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                height=820,
                on_select="rerun",
                selection_mode="single-row"
            )
            
            # Get selected row
            if selected_indices and len(selected_indices['selection']['rows']) > 0:
                selected_idx = selected_indices['selection']['rows'][0]
                st.session_state['selected_record'] = records[selected_idx]
        
        with col_detail:
            st.subheader("🔍 Detail Informasi")
            
            if 'selected_record' in st.session_state and st.session_state['selected_record']:
                record = st.session_state['selected_record']
                
                # Display image with authenticated access
                if 'url' in record or 'blob_url' in record:
                    img_url = record.get('url') or record.get('blob_url')
                    
                    with st.spinner('Memuat gambar...'):
                        img = load_image_from_blob(img_url)
                        if img:
                            st.image(img, use_container_width=True)
                        else:
                            st.warning("⚠️ Gambar tidak dapat dimuat")
                
                # Status
                status = record.get('helmet_status', 'unknown')
                if status in ['helmet', 'compliant']:
                    st.markdown('<div class="status-compliant">✅ PATUH</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="status-violation">❌ MELANGGAR</div>', unsafe_allow_html=True)
                
                st.markdown("---")
                
                # Details
                st.markdown(f"**📁 Nama File:**")
                st.text(record.get('filename', 'N/A'))
                
                st.markdown(f"**📅 Tanggal & Waktu:**")
                if 'uploaded_at' in record:
                    upload_time = pd.to_datetime(record['uploaded_at'])
                    st.text(upload_time.strftime('%d %B %Y'))
                    st.text(upload_time.strftime('%H:%M:%S'))
                else:
                    st.text('N/A')
                
                st.markdown(f"**🎯 Confidence Rate:**")
                confidence = record.get('confidence', None)
                if confidence is not None:
                    st.text(f"{confidence*100:.1f}%")
                else:
                    st.text('N/A')
                
                st.markdown(f"**🔗 URL Gambar:**")
                img_url = record.get('url') or record.get('blob_url', 'N/A')
                if img_url != 'N/A':
                    st.text_input("", img_url, label_visibility="collapsed", disabled=True)
                else:
                    st.text('N/A')
                
                st.markdown(f"**🆔 Database ID:**")
                st.code(str(record.get('_id', 'N/A')), language=None)
            
            else:
                st.info("👈 Pilih baris dari tabel untuk melihat detail")
    
    else:
        st.warning("⚠️ Tidak ada data yang sesuai dengan filter")
        st.info("Coba ubah filter atau refresh data")

except Exception as e:
    st.error(f"⚠️ Terjadi kesalahan: {str(e)}")
    st.info("Pastikan koneksi database tersedia dan credentials benar.")