import streamlit as st
import pandas as pd
import numpy as np
import folium
import random
from streamlit_folium import st_folium
import plotly.express as px
import plotly.graph_objects as go
import networkx as nx
from datetime import datetime, timedelta
import json
import geopandas as gpd
from shapely.geometry import Point, Polygon
from openai import AzureOpenAI
import os
from pathlib import Path

# Page config
st.set_page_config(
    page_title="🛰️ JALAK-HIJAU | Environmental Crime Detection",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
def load_css():
    st.markdown("""
    <style>
    :root {
        --primary-green: #2E8B57;
        --coral-orange: #FF6B35;
        --alice-blue: #F0F8FF;
        --dark-slate: #2F4F4F;
        --success-green: #28A745;
        --warning-orange: #FFA500;
        --danger-red: #DC3545;
    }
    
    .main-header {
        background: linear-gradient(90deg, var(--primary-green), #228B22);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
    }
    
    .hero-metrics {
        background: linear-gradient(135deg, #FF6B35, #2E8B57);
        padding: 2rem;
        border-radius: 15px;
        margin: 2rem 0;
        color: white;
        text-align: center;
    }
    
    .alert-critical {
        background-color: #FFE6E6;
        border-left: 5px solid var(--danger-red);
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    .alert-warning {
        background-color: #FFF8E1;
        border-left: 5px solid var(--warning-orange);
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    .alert-info {
        background-color: #E3F2FD;
        border-left: 5px solid #2196F3;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    .investigation-panel {
        background: linear-gradient(135deg, #FF6B35, #DC3545);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        border-left: 5px solid var(--primary-green);
        margin: 1rem 0;
    }
    
    .risk-high { color: var(--danger-red); font-weight: bold; }
    .risk-medium { color: var(--warning-orange); font-weight: bold; }
    .risk-low { color: var(--success-green); font-weight: bold; }
    
    .live-detection {
        animation: pulse 2s infinite;
        background: #FFE6E6;
        border: 2px solid #DC3545;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(220, 53, 69, 0.7); }
        70% { box-shadow: 0 0 0 10px rgba(220, 53, 69, 0); }
        100% { box-shadow: 0 0 0 0 rgba(220, 53, 69, 0); }
    }
    </style>
    """, unsafe_allow_html=True)

# Initialize session state
def init_session_state():
    if 'selected_alert' not in st.session_state:
        st.session_state.selected_alert = None
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'investigation_mode' not in st.session_state:
        st.session_state.investigation_mode = False
    if 'investigation_data' not in st.session_state:
        st.session_state.investigation_data = {}

# Data loading functions
@st.cache_data
def load_geospatial_data():
    """Load actual shapefiles or create realistic demo data"""
    try:
        forest_gdf = gpd.read_file("forest.shp")
        sawit_gdf = gpd.read_file("sawit.shp")
        overlap_gdf = gpd.read_file("overlap.shp")
        st.success("✅ Loaded actual shapefiles successfully!")
        return forest_gdf, sawit_gdf, overlap_gdf
    except Exception as e:
        st.warning(f"⚠️ Shapefiles not found, using demo data. Error: {str(e)}")
        return generate_realistic_geodata()

@st.cache_data
def load_financial_data():
    """Load financial transaction data"""
    data_dir = Path("data")
    
    if not data_dir.exists():
        st.warning("⚠️ Data directory not found. Run financial_data_generator.py first or using demo data.")
        return generate_demo_financial_data()
    
    try:
        transactions_df = pd.read_csv(data_dir / "transactions.csv")
        high_risk_df = pd.read_csv(data_dir / "transactions_high_risk.csv")
        clusters_df = pd.read_csv(data_dir / "transactions_clusters.csv")
        bank_accounts_df = pd.read_csv(data_dir / "bank_accounts.csv")
        
        # Convert date columns
        transactions_df['transaction_date'] = pd.to_datetime(transactions_df['transaction_date'])
        high_risk_df['transaction_date'] = pd.to_datetime(high_risk_df['transaction_date'])
        
        st.success(f"✅ Loaded financial data: {len(transactions_df):,} transactions, {len(high_risk_df):,} high-risk")
        return transactions_df, high_risk_df, clusters_df, bank_accounts_df
        
    except Exception as e:
        st.warning(f"⚠️ Error loading financial data. Using demo data.")
        return generate_demo_financial_data()

@st.cache_data  
def load_company_data():
    """Load company data"""
    data_dir = Path("data")
    
    try:
        # Try to load generated PT data first
        pt_df = pd.read_csv(data_dir / "pt_data.csv")
        st.success(f"✅ Loaded {len(pt_df)} companies from generated data")
        return pt_df
    except:
        try:
            # Fallback to jalak_hijau_pt_data.csv
            pt_df = pd.read_csv("jalak_hijau_pt_data.csv")
            st.success(f"✅ Loaded {len(pt_df)} companies from jalak_hijau_pt_data.csv")
            return pt_df
        except:
            st.warning("⚠️ No company data found, using demo data")
            return generate_demo_companies()

def generate_realistic_geodata():
    """Generate realistic geospatial data for demo"""
    regions = {
        'Riau': {'center': [0.5, 101.4], 'bbox': [(-1, 100), (2, 103)]},
        'Kalimantan Selatan': {'center': [-2.2, 115.0], 'bbox': [(-4, 113), (-1, 117)]},
        'Sumatera Utara': {'center': [2.0, 99.0], 'bbox': [(0, 97), (4, 101)]}
    }
    
    forest_areas = []
    sawit_concessions = []
    overlap_areas = []
    
    for region_name, region_data in regions.items():
        center_lat, center_lon = region_data['center']
        
        # Generate forest protected areas
        for i in range(15):
            lat = center_lat + np.random.uniform(-1, 1)
            lon = center_lon + np.random.uniform(-1.5, 1.5)
            size = np.random.uniform(0.1, 0.3)
            
            forest_polygon = Point(lon, lat).buffer(size)
            forest_areas.append({
                'geometry': forest_polygon,
                'name': f'Hutan Lindung {region_name} {i+1}',
                'region': region_name,
                'status': 'Protected',
                'area_ha': int(size * 111000 * 111000),
                'center_lat': lat,
                'center_lon': lon
            })
        
        # Generate palm concessions (some overlapping)
        for i in range(10):
            if i < 3:  # Create overlapping concessions
                base_forest = forest_areas[-3 + i]
                lat = base_forest['center_lat'] + np.random.uniform(-0.05, 0.05)
                lon = base_forest['center_lon'] + np.random.uniform(-0.05, 0.05)
                overlap_pct = np.random.uniform(0.15, 0.45)
            else:
                lat = center_lat + np.random.uniform(-1, 1)
                lon = center_lon + np.random.uniform(-1.5, 1.5)
                overlap_pct = 0
            
            size = np.random.uniform(0.05, 0.2)
            company_id = f"PT SAWIT {region_name.upper()} {i+1:02d}"
            
            sawit_polygon = Point(lon, lat).buffer(size)
            concession_data = {
                'geometry': sawit_polygon,
                'company': company_id,
                'region': region_name,
                'permit_status': 'Active',
                'area_ha': int(size * 111000 * 111000),
                'center_lat': lat,
                'center_lon': lon,
                'overlap_percentage': overlap_pct * 100,
                'is_overlapping': overlap_pct > 0,
                'risk_score': 85 + int(overlap_pct * 15) if overlap_pct > 0 else np.random.randint(20, 40)
            }
            sawit_concessions.append(concession_data)
            
            # Create overlap areas for overlapping concessions
            if overlap_pct > 0:
                overlap_size = size * overlap_pct
                overlap_polygon = Point(lon, lat).buffer(overlap_size)
                overlap_areas.append({
                    'geometry': overlap_polygon,
                    'company': company_id,
                    'forest_area': base_forest['name'],
                    'overlap_ha': int(overlap_size * 111000 * 111000),
                    'overlap_percentage': overlap_pct * 100,
                    'severity': 'CRITICAL' if overlap_pct > 0.3 else 'HIGH',
                    'center_lat': lat,
                    'center_lon': lon
                })
    
    forest_gdf = gpd.GeoDataFrame(forest_areas)
    sawit_gdf = gpd.GeoDataFrame(sawit_concessions)
    overlap_gdf = gpd.GeoDataFrame(overlap_areas)
    
    return forest_gdf, sawit_gdf, overlap_gdf

def generate_demo_financial_data():
    """Generate demo financial data"""
    # Generate demo transactions
    transactions = []
    for i in range(1000):
        transactions.append({
            'transaction_id': f'TXN_{i+1:06d}',
            'transaction_date': datetime.now() - timedelta(days=np.random.randint(0, 365)),
            'sender_company': f'PT Company {np.random.randint(1, 20)}',
            'receiver_company': f'PT Company {np.random.randint(1, 20)}',
            'amount_idr': random.randint(1000000, 5000000000),  # Use random instead of np.random
            'risk_score': np.random.randint(0, 100),
            'is_flagged': np.random.random() < 0.2,
            'transaction_type': np.random.choice(['normal_business', 'structuring', 'layering'])
        })
    
    transactions_df = pd.DataFrame(transactions)
    high_risk_df = transactions_df[transactions_df['risk_score'] > 70]
    
    clusters = []
    for i in range(5):
        clusters.append({
            'cluster_id': f'CLUSTER_{i+1:03d}',
            'companies_involved': [f'PT Company {j}' for j in range(i+1, i+4)],
            'transaction_count': np.random.randint(10, 50),
            'total_amount': random.randint(1000000000, 10000000000),  # Use random instead of np.random
            'risk_level': np.random.choice(['HIGH', 'MEDIUM', 'LOW'])
        })
    
    clusters_df = pd.DataFrame(clusters)
    bank_accounts_df = pd.DataFrame()  # Empty for demo
    
    return transactions_df, high_risk_df, clusters_df, bank_accounts_df

def generate_demo_companies():
    """Generate demo company data"""
    companies = []
    company_names = [
        'PT BERKAH SAWIT NUSANTARA', 'PT HIJAU SEJAHTERA ABADI',
        'PT CAHAYA PALM MANDIRI', 'PT DUTA KELAPA SAWIT',
        'PT KARYA UTAMA CONSULTING', 'PT PRIMA JAYA TRADING'
    ]
    
    for i, name in enumerate(company_names):
        companies.append({
            'company_id': f'COMP_{i+1:03d}',
            'nama_perseroan': name,
            'is_suspicious': i >= 4,
            'risk_score': np.random.randint(70, 95) if i >= 4 else np.random.randint(20, 50),
            'modal_disetor': np.random.randint(1000000000, 10000000000)
        })
    
    return pd.DataFrame(companies)

# OpenAI Integration
def setup_openai():
    """Setup Azure OpenAI client"""
    try:
        endpoint = os.getenv('AZURE_OPENAI_ENDPOINT') or st.secrets.get('AZURE_OPENAI_ENDPOINT')
        api_key = os.getenv('AZURE_OPENAI_API_KEY') or st.secrets.get('AZURE_OPENAI_API_KEY')
        api_version = os.getenv('AZURE_OPENAI_API_VERSION') or st.secrets.get('AZURE_OPENAI_API_VERSION', '2024-08-01-preview')
        
        if api_key and endpoint:
            client = AzureOpenAI(
                api_key=api_key,
                api_version=api_version,
                azure_endpoint=endpoint
            )
            return client
        else:
            return None
    except Exception as e:
        st.error(f"Error setting up Azure OpenAI: {str(e)}")
        return None

def generate_ai_analysis(client, data_context, user_query):
    """Generate AI-powered analysis"""
    if not client:
        return "AI Assistant tidak tersedia. Pastikan Azure OpenAI sudah dikonfigurasi dengan benar."
    
    try:
        prompt = f"""
        Anda adalah AI Assistant untuk sistem JALAK-HIJAU yang mendeteksi kejahatan lingkungan dan pencucian uang di Indonesia.
        
        Konteks data: {data_context}
        Pertanyaan user: {user_query}
        
        Berikan analisis yang spesifik, actionable, dan dalam bahasa Indonesia. 
        Fokus pada:
        1. Pola mencurigakan yang terdeteksi
        2. Rekomendasi investigasi konkret
        3. Risiko yang perlu ditindaklanjuti
        4. Langkah-langkah investigasi selanjutnya
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Anda adalah expert analyst untuk PPATK Indonesia yang spesialis dalam mendeteksi environmental crime dan money laundering."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.7
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"Error dalam analisis AI: {str(e)}. Periksa konfigurasi Azure OpenAI."

# Investigation Mode Functions
def start_investigation(alert_id, alert_data):
    """Initialize investigation mode"""
    st.session_state.investigation_mode = True
    st.session_state.selected_alert = alert_id
    
    investigation_data = {
        'alert_id': alert_id,
        'status': 'ACTIVE',
        'priority': 'HIGH',
        'assigned_to': 'Tim Investigasi PPATK',
        'start_date': datetime.now(),
        'case_summary': alert_data,
        'evidence_collected': [],
        'next_actions': [],
        'timeline': []
    }
    
    # Add evidence based on alert type
    if 'overlap' in alert_data.get('type', '').lower():
        investigation_data['evidence_collected'] = [
            '🛰️ Citra satelit menunjukkan overlap 127 ha',
            '📋 Izin HGU tidak mencakup area hutan lindung', 
            '💰 Transfer Rp 45M ke shell company sehari setelah clearing',
            '🏢 Beneficial owner: Ahmad Wijaya'
        ]
        investigation_data['next_actions'] = [
            '🔍 Verifikasi lapangan koordinat overlap',
            '📞 Koordinasi dengan KLHK untuk status kawasan',
            '🏦 Request rekening koran semua entitas terkait',
            '👤 Background check beneficial owner'
        ]
    elif 'transaksi' in alert_data.get('type', '').lower():
        investigation_data['evidence_collected'] = [
            '💰 Pola structuring: 12 transaksi di bawah Rp 500M',
            '🕸️ Network: 5 perusahaan shell terkait',
            '📊 Total dana mencurigakan: Rp 2.8 miliar',
            '⏰ Timing: Semua transaksi dalam 48 jam'
        ]
        investigation_data['next_actions'] = [
            '🔍 Analisis mendalam pola transaksi',
            '🏦 Freeze account sementara',
            '📋 Trace beneficial ownership',
            '👥 Koordinasi dengan unit cyber crime'
        ]
    
    st.session_state.investigation_data = investigation_data

def create_investigation_dashboard():
    """Create investigation mode dashboard"""
    if not st.session_state.investigation_mode:
        st.error("Investigation mode not active!")
        return
    
    inv_data = st.session_state.investigation_data
    
    st.markdown(f"""
    <div class="investigation-panel">
        <h2>🔍 INVESTIGATION MODE - {inv_data['alert_id']}</h2>
        <p><strong>Status:</strong> {inv_data['status']} | <strong>Priority:</strong> {inv_data['priority']} | <strong>Assigned:</strong> {inv_data['assigned_to']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Case Overview", "🔍 Evidence", "🎯 Actions", "📊 Analysis"])
    
    with tab1:
        st.subheader("Case Summary")
        case = inv_data['case_summary']
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            **Alert ID:** {case['id']}  
            **Company:** {case['company']}  
            **Location:** {case['location']}  
            **Risk Level:** <span class="risk-high">{case['risk']}</span>  
            **Type:** {case['type']}
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            **Investigation Start:** {inv_data['start_date'].strftime('%Y-%m-%d %H:%M')}  
            **Days Active:** {(datetime.now() - inv_data['start_date']).days}  
            **Progress:** 35% Complete  
            **Est. Completion:** 7 days
            """)
    
    with tab2:
        st.subheader("🔍 Evidence Collected")
        for i, evidence in enumerate(inv_data['evidence_collected']):
            st.markdown(f"**{i+1}.** {evidence}")
        
        new_evidence = st.text_input("Add New Evidence:")
        if st.button("➕ Add Evidence") and new_evidence:
            inv_data['evidence_collected'].append(f"📝 {new_evidence}")
            st.session_state.investigation_data = inv_data
            st.rerun()
    
    with tab3:
        st.subheader("🎯 Next Actions")
        for i, action in enumerate(inv_data['next_actions']):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**{i+1}.** {action}")
            with col2:
                if st.button("✅", key=f"complete_{i}"):
                    st.success(f"Action {i+1} marked complete!")
        
        new_action = st.text_input("Add New Action:")
        if st.button("➕ Add Action") and new_action:
            inv_data['next_actions'].append(f"🎯 {new_action}")
            st.session_state.investigation_data = inv_data
            st.rerun()
    
    with tab4:
        # Network analysis for investigation
        st.subheader("📊 Investigation Analysis")
        
        G = nx.DiGraph()
        G.add_node("PT BERKAH SAWIT", type="front_company", risk=95)
        G.add_node("Ahmad Wijaya", type="beneficial_owner", risk=90)
        G.add_node("PT KARYA SHELL", type="shell_company", risk=85)
        G.add_node("Bank Account A", type="account", risk=70)
        G.add_node("Bank Account B", type="account", risk=80)
        
        G.add_edge("Ahmad Wijaya", "PT BERKAH SAWIT", weight=0.9, relation="owner")
        G.add_edge("PT BERKAH SAWIT", "Bank Account A", weight=0.8, relation="transfer")
        G.add_edge("Bank Account A", "Bank Account B", weight=0.7, relation="layering")
        G.add_edge("Bank Account B", "PT KARYA SHELL", weight=0.9, relation="placement")
        
        pos = nx.spring_layout(G)
        
        edge_x, edge_y = [], []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
        
        node_x, node_y, node_text, node_colors = [], [], [], []
        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            node_text.append(node)
            
            node_type = G.nodes[node].get('type', 'unknown')
            if node_type == 'beneficial_owner':
                node_colors.append('red')
            elif node_type == 'front_company':
                node_colors.append('orange')
            elif node_type == 'shell_company':
                node_colors.append('darkred')
            else:
                node_colors.append('lightblue')
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=edge_x, y=edge_y, line=dict(width=2, color='gray'), 
                                hoverinfo='none', mode='lines'))
        fig.add_trace(go.Scatter(x=node_x, y=node_y, mode='markers+text', hoverinfo='text',
                                text=node_text, textposition="top center",
                                marker=dict(size=30, color=node_colors, line=dict(width=2, color='white')),
                                hovertext=[f"{node}<br>Risk: {G.nodes[node].get('risk', 0)}" for node in G.nodes()]))
        
        fig.update_layout(title="Network Analysis - Investigation Case", showlegend=False, hovermode='closest',
                         xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                         yaxis=dict(showgrid=False, zeroline=False, showticklabels=False), height=400)
        
        st.plotly_chart(fig, use_container_width=True)

# Enhanced Dashboard Functions


def create_overview_dashboard():
    
    
    # Load all data
    forest_gdf, sawit_gdf, overlap_gdf = load_geospatial_data()
    transactions_df, high_risk_df, clusters_df, bank_accounts_df = load_financial_data()
    companies_df = load_company_data()
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        critical_overlaps = len(overlap_gdf[overlap_gdf.get('severity', '') == 'CRITICAL']) if len(overlap_gdf) > 0 else 3
        st.metric("🚨 Critical Overlaps", f"{critical_overlaps}", delta="Real-time Detection")
    
    with col2:
        high_risk_transactions = len(high_risk_df) if len(high_risk_df) > 0 else 156
        st.metric("💰 High Risk Transactions", f"{high_risk_transactions:,}", delta="+23 today")
    
    with col3:
        total_companies = len(companies_df)
        suspicious_companies = len(companies_df[companies_df.get('is_suspicious', False) == True]) if 'is_suspicious' in companies_df.columns else 8
        st.metric("🏢 Suspicious Companies", f"{suspicious_companies}/{total_companies}", delta="Network Detected")
    
    with col4:
        st.metric("⏱️ Detection Time", "< 10 days", delta="-30% improvement", delta_color="inverse")
    
    # Full-width map
    st.subheader("🗺️ Real-time Environmental Risk Map")
    
    center_lat, center_lon = -2.5, 118.0
    m = folium.Map(location=[center_lat, center_lon], zoom_start=5)
    
    # Add forest areas
    if len(forest_gdf) > 0:
        for idx, forest in forest_gdf.iterrows():
            if hasattr(forest, 'center_lat') and hasattr(forest, 'center_lon'):
                folium.CircleMarker(
                    location=[forest.center_lat, forest.center_lon],
                    radius=8,
                    popup=f"🌲 {forest.get('name', 'Protected Forest')}<br>Region: {forest.get('region', 'Unknown')}<br>Area: {forest.get('area_ha', 0):,} ha",
                    color='green', fill=True, fillColor='green', fillOpacity=0.4
                ).add_to(m)
    
    # Add palm concessions
    if len(sawit_gdf) > 0:
        for idx, sawit in sawit_gdf.iterrows():
            if hasattr(sawit, 'center_lat') and hasattr(sawit, 'center_lon'):
                is_overlapping = sawit.get('is_overlapping', False)
                risk_score = sawit.get('risk_score', 30)
                
                if is_overlapping or risk_score > 70:
                    color, risk_level, icon = 'red', 'CRITICAL', 'exclamation-triangle'
                elif risk_score > 40:
                    color, risk_level, icon = 'orange', 'MEDIUM', 'warning'
                else:
                    color, risk_level, icon = 'blue', 'LOW', 'leaf'
                
                folium.Marker(
                    location=[sawit.center_lat, sawit.center_lon],
                    popup=f"""<div style="width: 300px;">
                        <h4>🏭 {sawit.get('company', 'Palm Company')}</h4><hr>
                        <b>Region:</b> {sawit.get('region', 'Unknown')}<br>
                        <b>Area:</b> {sawit.get('area_ha', 0):,} ha<br>
                        <b>Risk Score:</b> {risk_score}/100<br>
                        <b>Risk Level:</b> <span style="color: {color}; font-weight: bold;">{risk_level}</span><br>
                        {"<b style='color: red;'>⚠️ OVERLAPS WITH PROTECTED FOREST</b><br>" if is_overlapping else ""}
                        <b>Overlap:</b> {sawit.get('overlap_percentage', 0):.1f}%</div>""",
                    icon=folium.Icon(color=color, icon=icon)
                ).add_to(m)
    
    # Display full-width map
    map_data = st_folium(m, width=None, height=600)
    
    # Live detection simulation
    if np.random.random() < 0.3:  # 30% chance to show live detection
        st.markdown("""
        <div class="live-detection">
            <h4>🔴 LIVE DETECTION - New suspicious activity detected!</h4>
            <p>⚠️ <strong>PT SAWIT BARU 123</strong> - CRITICAL RISK<br>
            💰 Transfer: Rp 67M | 🕐 Detected: Real-time<br>
            📍 Location: Overlap dengan Hutan Lindung Riau</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Enhanced alert feed with mixed scenarios
    st.subheader("🚨 Real-time Alert Feed")
    
    alerts = []
    
    # Environmental alerts from geospatial data
    if len(overlap_gdf) > 0:
        for idx, overlap in overlap_gdf.head(2).iterrows():
            alerts.append({
                'id': f'ALT-GEO-{1156 + idx:04d}',
                'time': f'{14 - idx}:23 WIB',
                'location': overlap.get('forest_area', 'Protected Area'),
                'type': 'Forest-Concession Overlap',
                'risk': overlap.get('severity', 'HIGH'),
                'company': overlap.get('company', 'Unknown'),
                'details': f"Overlap: {overlap.get('overlap_percentage', 0):.1f}% ({overlap.get('overlap_ha', 0):,} ha)",
                'alert_source': 'geospatial'
            })
    
    # Financial alerts from transaction data
    if len(high_risk_df) > 0:
        recent_high_risk = high_risk_df.nlargest(2, 'risk_score')
        for idx, trans in recent_high_risk.iterrows():
            alerts.append({
                'id': f'ALT-FIN-{2156 + idx:04d}',
                'time': f'{13 - idx}:45 WIB',
                'location': 'Financial Network',
                'type': 'Suspicious Transaction Pattern',
                'risk': 'HIGH' if trans['risk_score'] > 85 else 'MEDIUM',
                'company': trans.get('sender_company', 'Unknown'),
                'details': f"Amount: Rp {trans['amount_idr']:,} | Risk: {trans['risk_score']}/100",
                'alert_source': 'financial'
            })
    
    # Fallback demo alerts
    if not alerts:
        alerts = [
            {
                'id': 'ALT-GEO-0156', 'time': '14:23 WIB', 'location': 'Riau Province',
                'type': 'Forest-Concession Overlap', 'risk': 'CRITICAL',
                'company': 'PT BERKAH SAWIT NUSANTARA', 'details': 'Overlap: 35.2% (127 ha)',
                'alert_source': 'geospatial'
            },
            {
                'id': 'ALT-FIN-0157', 'time': '13:45 WIB', 'location': 'Financial Network',
                'type': 'Suspicious Transaction Pattern', 'risk': 'HIGH',
                'company': 'PT HIJAU SEJAHTERA ABADI', 'details': 'Structuring: 12 transactions < Rp 500M',
                'alert_source': 'financial'
            }
        ]
    
    # Display alerts
    for alert in alerts[:4]:  # Show top 4 alerts
        risk_class = f"risk-{alert['risk'].lower()}"
        alert_class = "alert-critical" if alert['risk'] == 'CRITICAL' else "alert-warning" if alert['risk'] == 'HIGH' else "alert-info"
        
        # Icon based on alert source
        icon = '🛰️' if alert['alert_source'] == 'geospatial' else '💰'
        
        st.markdown(f"""
        <div class="{alert_class}">
            <strong>{icon} Alert {alert['id']}</strong> - {alert['time']}<br>
            <strong>Source:</strong> {alert['alert_source'].title()}<br>
            <strong>Location:</strong> {alert['location']}<br>
            <strong>Type:</strong> {alert['type']}<br>
            <strong>Company:</strong> {alert['company']}<br>
            <strong>Details:</strong> {alert.get('details', 'N/A')}<br>
            <strong>Risk Level:</strong> <span class="{risk_class}">{alert['risk']}</span>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button(f"🔍 Start Investigation", key=f"investigate_{alert['id']}"):
            start_investigation(alert['id'], alert)
            st.success(f"✅ Investigation {alert['id']} started!")
            st.rerun()

def create_analysis_page():
    """Enhanced analysis page with side-by-side map and network analysis"""
    st.header("📊 Advanced Analysis Dashboard")
    st.subheader("Comprehensive Geospatial & Network Intelligence")
    
    # Load data
    forest_gdf, sawit_gdf, overlap_gdf = load_geospatial_data()
    transactions_df, high_risk_df, clusters_df, bank_accounts_df = load_financial_data()
    companies_df = load_company_data()
    
    # Single column controls
    st.markdown("### 🎛️ Analysis Controls")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        analysis_mode = st.selectbox("Analysis Mode", 
                                   ["Comprehensive Overview", "Geospatial Focus", "Network Focus", "Financial Focus"])
    
    with col2:
        risk_filter = st.selectbox("Risk Level Filter", ["All Levels", "Critical Only", "High+", "Medium+"])
    
    with col3:
        time_period = st.selectbox("Time Period", ["Last 30 days", "Last 90 days", "Last Year", "All Time"])
    
    # Two-column layout for Map and Network Analysis
    st.markdown("### 🗺️ Geospatial Analysis | 🕸️ Network Analysis")
    
    col_map, col_network = st.columns(2)
    
    # LEFT COLUMN - Geospatial Analysis
    with col_map:
        st.markdown("#### 🛰️ Satellite-based Risk Detection")
        
        # Create focused map
        center_lat, center_lon = -2.5, 118.0
        m = folium.Map(location=[center_lat, center_lon], zoom_start=6)
        
        # Add geospatial data to map
        if len(forest_gdf) > 0:
            for idx, forest in forest_gdf.iterrows():
                if hasattr(forest, 'center_lat') and hasattr(forest, 'center_lon'):
                    folium.CircleMarker(
                        location=[forest.center_lat, forest.center_lon], radius=6,
                        popup=f"🌲 {forest.get('name', 'Protected Forest')}", color='green',
                        fill=True, fillColor='green', fillOpacity=0.3
                    ).add_to(m)
        
        if len(sawit_gdf) > 0:
            for idx, sawit in sawit_gdf.iterrows():
                if hasattr(sawit, 'center_lat') and hasattr(sawit, 'center_lon'):
                    is_overlapping = sawit.get('is_overlapping', False)
                    color = 'red' if is_overlapping else 'orange'
                    
                    folium.CircleMarker(
                        location=[sawit.center_lat, sawit.center_lon], radius=8,
                        popup=f"🏭 {sawit.get('company', 'Palm Company')}<br>Risk: {'HIGH' if is_overlapping else 'MEDIUM'}",
                        color=color, fill=True, fillColor=color, fillOpacity=0.7
                    ).add_to(m)
        
        # Display map
        map_data = st_folium(m, width=400, height=400)
        
        # Geospatial metrics
        if len(overlap_gdf) > 0:
            total_overlap_area = overlap_gdf['overlap_ha'].sum() if 'overlap_ha' in overlap_gdf.columns else 456
            critical_overlaps = len(overlap_gdf[overlap_gdf.get('severity', '') == 'CRITICAL'])
            
            st.metric("🌲 Total Illegal Overlap", f"{total_overlap_area:,} ha")
            st.metric("🚨 Critical Cases", critical_overlaps)
    
    # RIGHT COLUMN - Network Analysis  
    with col_network:
        st.markdown("#### 🕸️ Corporate Network Intelligence")
        
        # Create network graph from company and transaction data
        G = nx.Graph()
        
        # Add company nodes
        suspicious_companies = companies_df[companies_df.get('is_suspicious', False) == True] if 'is_suspicious' in companies_df.columns else companies_df.head(3)
        
        for idx, company in suspicious_companies.iterrows():
            company_name = company.get('nama_perseroan', f'Company {idx}')
            risk_score = company.get('risk_score', 50)
            G.add_node(company_name, 
                      type='company', 
                      risk=risk_score, 
                      suspicious=company.get('is_suspicious', False))
        
        # Add connections based on transaction patterns
        if len(high_risk_df) > 0:
            # Create edges between companies that have transactions
            company_pairs = set()
            for idx, trans in high_risk_df.head(20).iterrows():
                sender = trans.get('sender_company', '')
                receiver = trans.get('receiver_company', '')
                if sender and receiver and sender != receiver:
                    company_pairs.add((sender, receiver))
            
            for sender, receiver in list(company_pairs)[:10]:  # Limit connections
                if sender in G.nodes() or receiver in G.nodes():
                    if sender not in G.nodes():
                        G.add_node(sender, type='related', risk=60)
                    if receiver not in G.nodes():
                        G.add_node(receiver, type='related', risk=60)
                    G.add_edge(sender, receiver, weight=0.8)
        
        # If no transaction data, create demo network
        if len(G.nodes()) < 3:
            demo_companies = ['PT BERKAH SAWIT', 'PT KARYA SHELL', 'Ahmad Wijaya', 'PT PRIMA TRADING']
            for company in demo_companies:
                G.add_node(company, type='company', risk=np.random.randint(60, 95))
            G.add_edge('Ahmad Wijaya', 'PT BERKAH SAWIT', weight=0.9)
            G.add_edge('PT BERKAH SAWIT', 'PT KARYA SHELL', weight=0.8)
            G.add_edge('PT KARYA SHELL', 'PT PRIMA TRADING', weight=0.7)
        
        # Create network visualization
        if len(G.nodes()) > 0:
            pos = nx.spring_layout(G, k=2, iterations=50)
            
            # Prepare data for plotly
            edge_x, edge_y = [], []
            for edge in G.edges():
                if edge[0] in pos and edge[1] in pos:
                    x0, y0 = pos[edge[0]]
                    x1, y1 = pos[edge[1]]
                    edge_x.extend([x0, x1, None])
                    edge_y.extend([y0, y1, None])
            
            node_x, node_y, node_text, node_colors, node_sizes = [], [], [], [], []
            for node in G.nodes():
                if node in pos:
                    x, y = pos[node]
                    node_x.append(x)
                    node_y.append(y)
                    node_text.append(node[:20] + '...' if len(node) > 20 else node)
                    
                    risk = G.nodes[node].get('risk', 50)
                    if risk > 80:
                        node_colors.append('red')
                    elif risk > 60:
                        node_colors.append('orange')
                    else:
                        node_colors.append('lightblue')
                    
                    node_sizes.append(max(15, risk/4))
            
            # Create plotly network graph
            fig_network = go.Figure()
            
            # Add edges
            fig_network.add_trace(go.Scatter(
                x=edge_x, y=edge_y, line=dict(width=1, color='gray'),
                hoverinfo='none', mode='lines', showlegend=False
            ))
            
            # Add nodes
            fig_network.add_trace(go.Scatter(
                x=node_x, y=node_y, mode='markers+text', hoverinfo='text',
                text=node_text, textposition="bottom center", textfont=dict(size=8),
                marker=dict(size=node_sizes, color=node_colors, 
                           line=dict(width=1, color='white')),
                hovertext=[f"{node}<br>Risk: {G.nodes[node].get('risk', 0)}/100" for node in G.nodes() if node in pos],
                showlegend=False
            ))
            
            fig_network.update_layout(
                title="Suspicious Network Connections",
                showlegend=False, hovermode='closest',
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                height=400, margin=dict(t=30, b=0, l=0, r=0)
            )
            
            st.plotly_chart(fig_network, use_container_width=True)
            
            # Network metrics
            st.metric("🕸️ Network Nodes", len(G.nodes()))
            st.metric("🔗 Connections", len(G.edges()))
        else:
            st.info("No network data available")
    
    # Single column continuation - Financial Analysis
    st.markdown("### 💰 Financial Intelligence Dashboard")
    
    if len(transactions_df) > 0:
        # Financial metrics row
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_amount = transactions_df['amount_idr'].sum() if 'amount_idr' in transactions_df.columns else 125500000000000
            st.metric("Total Transaction Value", f"Rp {total_amount/1e12:.1f}T")
        
        with col2:
            high_risk_count = len(high_risk_df)
            st.metric("High Risk Transactions", f"{high_risk_count:,}")
        
        with col3:
            clusters_count = len(clusters_df) if len(clusters_df) > 0 else 5
            st.metric("Suspicious Clusters", clusters_count)
        
        with col4:
            risk_rate = (len(high_risk_df) / len(transactions_df) * 100) if len(transactions_df) > 0 else 15.3
            st.metric("Risk Detection Rate", f"{risk_rate:.1f}%")
        
        # Transaction analysis charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📈 Transaction Volume Trend")
            
            # Create time series of transactions
            if 'transaction_date' in transactions_df.columns:
                daily_stats = transactions_df.groupby(transactions_df['transaction_date'].dt.date).agg({
                    'amount_idr': 'sum',
                    'transaction_id': 'count'
                }).reset_index()
                daily_stats.columns = ['Date', 'Total_Amount', 'Count']
                
                fig_trend = px.line(daily_stats.tail(30), x='Date', y='Count',
                                   title="Daily Transaction Count (Last 30 days)")
                st.plotly_chart(fig_trend, use_container_width=True)
            else:
                # Demo time series
                dates = pd.date_range(start='2024-11-01', end='2024-12-05', freq='D')
                counts = np.random.poisson(45, len(dates))
                fig_trend = px.line(x=dates, y=counts, title="Daily Transaction Count")
                st.plotly_chart(fig_trend, use_container_width=True)
        
        with col2:
            st.markdown("#### 🎯 Risk Score Distribution")
            
            if 'risk_score' in transactions_df.columns:
                risk_scores = transactions_df['risk_score']
            else:
                risk_scores = np.random.normal(35, 20, 1000)
                risk_scores = np.clip(risk_scores, 0, 100)
            
            fig_risk = px.histogram(x=risk_scores, nbins=20, 
                                   title="Risk Score Distribution",
                                   color_discrete_sequence=['#2E8B57'])
            fig_risk.update_layout(xaxis_title="Risk Score", yaxis_title="Count")
            st.plotly_chart(fig_risk, use_container_width=True)
    
    # High-risk cases table
    st.markdown("### 🚨 High-Risk Cases Requiring Investigation")
    
    if len(high_risk_df) > 0:
        # Display top high-risk transactions
        display_df = high_risk_df.nlargest(10, 'risk_score')[
            ['transaction_id', 'transaction_date', 'sender_company', 'receiver_company', 
             'amount_idr', 'risk_score', 'transaction_type']
        ].copy()
        
        # Format for display
        display_df['amount_formatted'] = display_df['amount_idr'].apply(lambda x: f"Rp {x:,}")
        display_df['risk_indicator'] = display_df['risk_score'].apply(
            lambda x: '🔴' if x > 90 else '🟠' if x > 80 else '🟡'
        )
        
        st.dataframe(display_df[['transaction_id', 'transaction_date', 'sender_company', 
                                'receiver_company', 'amount_formatted', 'risk_score', 
                                'risk_indicator', 'transaction_type']], 
                    use_container_width=True)
    else:
        st.info("No high-risk transaction data available")

def create_ai_assistant():
    """AI Assistant page"""
    st.header("🤖 AI Assistant JALAK-HIJAU")
    st.subheader("Analisis Cerdas & Rekomendasi Investigasi")
    
    client = setup_openai()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("💬 Chat dengan AI Assistant")
        
        # Display chat history
        for chat in st.session_state.chat_history:
            if chat['role'] == 'user':
                st.markdown(f"""
                <div style="background-color: #E8F5E8; padding: 10px; border-radius: 10px; margin: 5px 0;">
                    <strong>👤 Anda:</strong> {chat['content']}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="background-color: #F0F8FF; padding: 10px; border-radius: 10px; margin: 5px 0;">
                    <strong>🤖 AI Assistant:</strong> {chat['content']}
                </div>
                """, unsafe_allow_html=True)
        
        # Chat input
        user_query = st.text_input("Tanya AI Assistant:", 
                                  placeholder="Contoh: Analisis pola transaksi PT BERKAH SAWIT")
        
        col_send, col_clear = st.columns([1, 4])
        
        with col_send:
            if st.button("📤 Kirim") and user_query:
                st.session_state.chat_history.append({'role': 'user', 'content': user_query})
                
                data_context = """
                JALAK-HIJAU telah mendeteksi 3 overlap kritis konsesi sawit dengan hutan lindung,
                156 transaksi berisiko tinggi dengan total nilai Rp 125T, dan 8 perusahaan shell
                dengan pola structuring dan layering yang mencurigakan.
                """
                
                ai_response = generate_ai_analysis(client, data_context, user_query)
                st.session_state.chat_history.append({'role': 'assistant', 'content': ai_response})
                st.rerun()
        
        with col_clear:
            if st.button("🗑️ Clear Chat"):
                st.session_state.chat_history = []
                st.rerun()
    
    with col2:
        st.subheader("🎯 Quick Actions")
        
        quick_queries = [
            "Analisis PT BERKAH SAWIT NUSANTARA",
            "Pola transaksi mencurigakan hari ini", 
            "Perusahaan dengan risk score tertinggi",
            "Generate laporan investigasi",
            "Rekomendasi prioritas tindakan",
            "Prediksi tren kejahatan lingkungan"
        ]
        
        for query in quick_queries:
            if st.button(f"💡 {query}", key=f"quick_{hash(query)}"):
                st.session_state.chat_history.append({'role': 'user', 'content': query})
                
                data_context = "Konteks sistem JALAK-HIJAU dengan data kasus aktual..."
                ai_response = generate_ai_analysis(client, data_context, query)
                
                st.session_state.chat_history.append({'role': 'assistant', 'content': ai_response})
                st.rerun()
        
        st.markdown("---")
        st.subheader("🧠 AI Capabilities")
        st.markdown("""
        **AI Assistant dapat:**
        - 🔍 Analisis pola geospasial dan transaksi
        - 📋 Generate laporan STR otomatis
        - 🎯 Rekomendasi investigasi prioritas
        - 🕸️ Identifikasi jaringan shell company
        - 📈 Prediksi tren kejahatan lingkungan
        - ⚡ Natural language investigation
        """)

# Main application
def main():
    load_css()
    init_session_state()
    
    # Check if in investigation mode
    if st.session_state.investigation_mode:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.title("🔍 JALAK-HIJAU Investigation Mode")
        
        with col2:
            if st.button("❌ Exit Investigation", type="secondary"):
                st.session_state.investigation_mode = False
                st.session_state.selected_alert = None
                st.session_state.investigation_data = {}
                st.rerun()
        
        create_investigation_dashboard()
        return
    
    # Sidebar
    
    st.sidebar.image("logo.png", width=300)
    st.sidebar.markdown("""
    <div style="text-align: center; padding: 20px;">
        <p style="color: white;">Environmental Crime Detection</p>
    </div>
    """,
    unsafe_allow_html=True
)
    
    # Navigation
    pages = {
        "🏠 Dashboard Utama": create_overview_dashboard,
        "📊 Advanced Analysis": create_analysis_page,
        "🤖 AI Assistant": create_ai_assistant
    }
    
    selected_page = st.sidebar.selectbox("Pilih Halaman", list(pages.keys()))
    
    # System status
    data_status = "✅ Loaded" if Path("data").exists() else "⚠️ Demo Mode"
    geo_status = "✅ Loaded" if Path("forest.shp").exists() else "⚠️ Demo Mode" 
    
    st.sidebar.markdown(f"""
    ---
    ### 📊 System Status
    - **🟢 Satellite Feed:** Active
    - **🟢 Financial Data:** {data_status}
    - **🟢 Geospatial Data:** {geo_status}
    - **🟢 AI Engine:** Online
    
    ### 📈 Today's Stats
    - **New Alerts:** 5
    - **High Risk Cases:** 12
    - **Active Investigations:** {1 if st.session_state.investigation_mode else 0}
    """)
    
    # Execute selected page
    pages[selected_page]()

if __name__ == "__main__":
    main()
