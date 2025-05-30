import streamlit as st
import pandas as pd
import numpy as np
import folium
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

# Page config
st.set_page_config(
    page_title="🛰️ JALAK-HIJAU | Environmental Crime Detection",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS (same as before)
def load_css():
    st.markdown("""
    <style>
    /* Main theme colors */
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
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        border-left: 5px solid var(--primary-green);
        margin: 1rem 0;
    }
    
    .investigation-panel {
        background: linear-gradient(135deg, #FF6B35, #DC3545);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    .risk-high { color: var(--danger-red); font-weight: bold; }
    .risk-medium { color: var(--warning-orange); font-weight: bold; }
    .risk-low { color: var(--success-green); font-weight: bold; }
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

# Enhanced data loading with real shapefiles
@st.cache_data
def load_geospatial_data():
    """Load actual shapefiles or create realistic demo data"""
    try:
        # Try to load actual shapefiles
        forest_gdf = gpd.read_file("map/forest.shp")
        sawit_gdf = gpd.read_file("map/sawit.shp")
        overlap_gdf = gpd.read_file("map/overlap.shp")
        
        st.success("✅ Loaded actual shapefiles successfully!")
        return forest_gdf, sawit_gdf, overlap_gdf
        
    except Exception as e:
        st.warning(f"⚠️ Shapefiles not found, using demo data. Error: {str(e)}")
        return generate_realistic_geodata()

def generate_realistic_geodata():
    """Generate more realistic geospatial data for demo"""
    # Focus on actual Indonesian palm oil regions
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
                'area_ha': int(size * 111000 * 111000),  # Rough conversion to hectares
                'center_lat': lat,
                'center_lon': lon
            })
        
        # Generate palm concessions (some overlapping)
        for i in range(10):
            if i < 3:  # Create overlapping concessions
                base_forest = forest_areas[-3 + i]
                lat = base_forest['center_lat'] + np.random.uniform(-0.05, 0.05)
                lon = base_forest['center_lon'] + np.random.uniform(-0.05, 0.05)
                overlap_pct = np.random.uniform(0.15, 0.45)  # 15-45% overlap
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

def calculate_overlap_analysis(forest_gdf, sawit_gdf, min_overlap_percent=10):
    """Calculate overlap analysis between forest and palm concessions"""
    overlap_results = []
    
    for idx_sawit, sawit in sawit_gdf.iterrows():
        for idx_forest, forest in forest_gdf.iterrows():
            try:
                if sawit.geometry.intersects(forest.geometry):
                    intersection = sawit.geometry.intersection(forest.geometry)
                    overlap_area = intersection.area
                    sawit_area = sawit.geometry.area
                    overlap_percentage = (overlap_area / sawit_area) * 100
                    
                    if overlap_percentage >= min_overlap_percent:
                        overlap_results.append({
                            'company': sawit.get('company', f'Company {idx_sawit}'),
                            'forest_name': forest.get('name', f'Forest {idx_forest}'),
                            'sawit_area_ha': sawit.get('area_ha', 0),
                            'overlap_percentage': overlap_percentage,
                            'overlap_area_ha': int(overlap_area * 111000 * 111000),
                            'risk_level': 'CRITICAL' if overlap_percentage > 30 else 'HIGH' if overlap_percentage > 15 else 'MEDIUM',
                            'center_lat': sawit.get('center_lat', 0),
                            'center_lon': sawit.get('center_lon', 0)
                        })
            except Exception as e:
                continue
    
    return pd.DataFrame(overlap_results)

# Investigation Mode Functions
def start_investigation(alert_id, alert_data):
    """Initialize investigation mode with specific alert"""
    st.session_state.investigation_mode = True
    st.session_state.selected_alert = alert_id
    
    # Create comprehensive investigation data
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
    
    # Add specific evidence based on alert type
    if 'overlap' in alert_data.get('type', '').lower():
        investigation_data['evidence_collected'] = [
            '🛰️ Citra satelit menunjukkan overlap 127 ha',
            '📋 Izin HGU PT BERKAH SAWIT tidak mencakup area hutan lindung', 
            '💰 Transfer Rp 45M ke shell company sehari setelah clearing',
            '🏢 Beneficial owner: Ahmad Wijaya (NIK: 1234567890123456)'
        ]
        
        investigation_data['next_actions'] = [
            '🔍 Verifikasi lapangan koordinat overlap',
            '📞 Koordinasi dengan KLHK untuk status kawasan',
            '🏦 Request rekening koran semua entitas terkait',
            '👤 Background check Ahmad Wijaya & keluarga'
        ]
    
    st.session_state.investigation_data = investigation_data

def create_investigation_dashboard():
    """Create investigation mode dashboard"""
    if not st.session_state.investigation_mode:
        st.error("Investigation mode not active!")
        return
    
    inv_data = st.session_state.investigation_data
    
    # Investigation header
    st.markdown(f"""
    <div class="investigation-panel">
        <h2>🔍 INVESTIGATION MODE - {inv_data['alert_id']}</h2>
        <p><strong>Status:</strong> {inv_data['status']} | <strong>Priority:</strong> {inv_data['priority']} | <strong>Assigned:</strong> {inv_data['assigned_to']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Investigation tabs
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
        
        # Add new evidence
        st.markdown("---")
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
        
        # Add new action
        st.markdown("---")
        new_action = st.text_input("Add New Action:")
        if st.button("➕ Add Action") and new_action:
            inv_data['next_actions'].append(f"🎯 {new_action}")
            st.session_state.investigation_data = inv_data
            st.rerun()
    
    with tab4:
        st.subheader("📊 Investigation Analysis")
        
        # Financial flow analysis
        st.markdown("### 💰 Financial Flow Analysis")
        
        # Create a simple network graph for the investigation
        G = nx.DiGraph()
        
        # Add nodes
        G.add_node("PT BERKAH SAWIT", type="front_company", risk=95)
        G.add_node("Ahmad Wijaya", type="beneficial_owner", risk=90)
        G.add_node("PT KARYA SHELL", type="shell_company", risk=85)
        G.add_node("Bank Account A", type="account", risk=70)
        G.add_node("Bank Account B", type="account", risk=80)
        
        # Add edges
        G.add_edge("Ahmad Wijaya", "PT BERKAH SAWIT", weight=0.9, relation="owner")
        G.add_edge("PT BERKAH SAWIT", "Bank Account A", weight=0.8, relation="transfer")
        G.add_edge("Bank Account A", "Bank Account B", weight=0.7, relation="layering")
        G.add_edge("Bank Account B", "PT KARYA SHELL", weight=0.9, relation="placement")
        
        # Create network visualization
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
        
        # Add edges
        fig.add_trace(go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=2, color='gray'),
            hoverinfo='none',
            mode='lines'
        ))
        
        # Add nodes
        fig.add_trace(go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            hoverinfo='text',
            text=node_text,
            textposition="top center",
            marker=dict(size=30, color=node_colors, line=dict(width=2, color='white')),
            hovertext=[f"{node}<br>Risk: {G.nodes[node].get('risk', 0)}" for node in G.nodes()]
        ))
        
        fig.update_layout(
            title="Network Analysis - PT BERKAH SAWIT Investigation",
            showlegend=False,
            hovermode='closest',
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Risk assessment
        st.markdown("### ⚠️ Risk Assessment")
        risk_metrics = {
            'Environmental Impact': 95,
            'Financial Crime': 88,
            'Regulatory Violation': 92,
            'Reputational Risk': 85
        }
        
        for metric, value in risk_metrics.items():
            st.metric(metric, f"{value}/100", delta=f"+{np.random.randint(5, 15)}")

# Enhanced Overview Dashboard with Real Data Integration
def create_overview_dashboard():
    """Enhanced main overview dashboard with real shapefile integration"""
    st.markdown("""
    <div class="main-header">
        <h1>🛰️ JALAK-HIJAU</h1>
        <h3>Environmental Crime Detection System</h3>
        <p>Sistem Deteksi Kejahatan Lingkungan & Pencucian Uang Terintegrasi</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Load geospatial data
    forest_gdf, sawit_gdf, overlap_gdf = load_geospatial_data()
    
    # Calculate overlap analysis
    overlap_analysis = calculate_overlap_analysis(forest_gdf, sawit_gdf, min_overlap_percent=10)
    
    # Enhanced metrics with real data
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        critical_overlaps = len(overlap_analysis[overlap_analysis['risk_level'] == 'CRITICAL']) if len(overlap_analysis) > 0 else len([c for c in sawit_gdf.to_dict('records') if c.get('is_overlapping', False)])
        st.metric(
            label="🚨 Critical Overlaps",
            value=f"{critical_overlaps}",
            delta="Real-time Detection"
        )
    
    with col2:
        high_risk_companies = len(sawit_gdf[sawit_gdf.get('risk_score', 0) > 70]) if 'risk_score' in sawit_gdf.columns else 8
        st.metric(
            label="🏢 High Risk Companies",
            value=f"{high_risk_companies}",
            delta="+2 today"
        )
    
    with col3:
        total_overlap_area = overlap_analysis['overlap_area_ha'].sum() if len(overlap_analysis) > 0 else 456
        st.metric(
            label="🌲 Total Overlap Area",
            value=f"{total_overlap_area:,} ha",
            delta="Illegal Expansion"
        )
    
    with col4:
        st.metric(
            label="⏱️ Detection Time",
            value="< 10 days",
            delta="-30% improvement",
            delta_color="inverse"
        )
    
    # Enhanced map with real overlap data
    st.subheader("🗺️ Real-time Environmental Risk Map")
    
    # Create map centered on Indonesia
    center_lat, center_lon = -2.5, 118.0
    m = folium.Map(location=[center_lat, center_lon], zoom_start=5)
    
    # Add forest areas (green)
    if len(forest_gdf) > 0:
        for idx, forest in forest_gdf.iterrows():
            if hasattr(forest, 'center_lat') and hasattr(forest, 'center_lon'):
                folium.CircleMarker(
                    location=[forest.center_lat, forest.center_lon],
                    radius=8,
                    popup=f"""
                    <b>🌲 {forest.get('name', 'Protected Forest')}</b><br>
                    Region: {forest.get('region', 'Unknown')}<br>
                    Status: {forest.get('status', 'Protected')}<br>
                    Area: {forest.get('area_ha', 0):,} ha
                    """,
                    color='green',
                    fill=True,
                    fillColor='green',
                    fillOpacity=0.4
                ).add_to(m)
    
    # Add palm concessions with risk-based coloring
    if len(sawit_gdf) > 0:
        for idx, sawit in sawit_gdf.iterrows():
            if hasattr(sawit, 'center_lat') and hasattr(sawit, 'center_lon'):
                is_overlapping = sawit.get('is_overlapping', False)
                risk_score = sawit.get('risk_score', 30)
                
                if is_overlapping or risk_score > 70:
                    color = 'red'
                    risk_level = 'CRITICAL'
                    icon = 'exclamation-triangle'
                elif risk_score > 40:
                    color = 'orange' 
                    risk_level = 'MEDIUM'
                    icon = 'warning'
                else:
                    color = 'blue'
                    risk_level = 'LOW'
                    icon = 'leaf'
                
                folium.Marker(
                    location=[sawit.center_lat, sawit.center_lon],
                    popup=f"""
                    <div style="width: 300px;">
                        <h4>🏭 {sawit.get('company', 'Palm Company')}</h4>
                        <hr>
                        <b>Region:</b> {sawit.get('region', 'Unknown')}<br>
                        <b>Area:</b> {sawit.get('area_ha', 0):,} ha<br>
                        <b>Risk Score:</b> {risk_score}/100<br>
                        <b>Risk Level:</b> <span style="color: {color}; font-weight: bold;">{risk_level}</span><br>
                        {"<b style='color: red;'>⚠️ OVERLAPS WITH PROTECTED FOREST</b><br>" if is_overlapping else ""}
                        <b>Overlap:</b> {sawit.get('overlap_percentage', 0):.1f}%
                    </div>
                    """,
                    icon=folium.Icon(color=color, icon=icon)
                ).add_to(m)
    
    # Display map
    map_data = st_folium(m, width=700, height=500)
    
    # Enhanced alert feed with real cases
    st.subheader("🚨 Real-time Alert Feed")
    
    # Generate alerts based on actual overlap data
    alerts = []
    if len(overlap_analysis) > 0:
        for idx, overlap in overlap_analysis.head(3).iterrows():
            alerts.append({
                'id': f'ALT-2024-{1156 + idx:04d}',
                'time': f'{14 - idx}:23 WIB',
                'location': 'Real Geospatial Detection',
                'type': 'Forest-Concession Overlap',
                'risk': overlap['risk_level'],
                'company': overlap['company'],
                'details': f"Overlap: {overlap['overlap_percentage']:.1f}% ({overlap['overlap_area_ha']:,} ha)"
            })
    else:
        # Fallback demo alerts
        alerts = [
            {
                'id': 'ALT-2024-0156',
                'time': '14:23 WIB',
                'location': 'Riau Province',
                'type': 'Forest-Concession Overlap',
                'risk': 'CRITICAL',
                'company': 'PT BERKAH SAWIT NUSANTARA',
                'details': 'Overlap: 35.2% (127 ha)'
            }
        ]
    
    for alert in alerts:
        risk_class = f"risk-{alert['risk'].lower()}"
        alert_class = "alert-critical" if alert['risk'] == 'CRITICAL' else "alert-warning"
        
        st.markdown(f"""
        <div class="{alert_class}">
            <strong>🚨 Alert {alert['id']}</strong> - {alert['time']}<br>
            <strong>Location:</strong> {alert['location']}<br>
            <strong>Type:</strong> {alert['type']}<br>
            <strong>Company:</strong> {alert['company']}<br>
            <strong>Details:</strong> {alert.get('details', 'N/A')}<br>
            <strong>Risk Level:</strong> <span class="{risk_class}">{alert['risk']}</span>
        </div>
        """, unsafe_allow_html=True)
        
        # Investigation button
        if st.button(f"🔍 Start Investigation", key=f"investigate_{alert['id']}"):
            start_investigation(alert['id'], alert)
            st.success(f"✅ Investigation {alert['id']} started!")
            st.rerun()

# Main application with investigation mode
def main():
    load_css()
    init_session_state()
    
    # Check if in investigation mode
    if st.session_state.investigation_mode:
        # Investigation mode interface
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
    
    # Normal dashboard mode
    st.sidebar.markdown("""
    <div style="text-align: center; padding: 20px;">
        <h2 style="color: white;">🛰️ JALAK-HIJAU</h2>
        <p style="color: white;">Environmental Crime Detection</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Navigation menu
    pages = {
        "🏠 Dashboard Utama": create_overview_dashboard,
        # Add other pages here as needed
    }
    
    selected_page = st.sidebar.selectbox("Pilih Halaman", list(pages.keys()))
    
    # System status
    st.sidebar.markdown(f"""
    ---
    ### 📊 System Status
    - **🟢 Satellite Feed:** Active
    - **🟢 Shapefile Integration:** {"✅ Loaded" if 'forest.shp' else "⚠️ Demo Mode"}
    - **🟢 Overlap Detection:** Running
    - **🟢 AI Engine:** Online
    
    ### 📈 Today's Stats
    - **New Overlaps Detected:** 3
    - **High Risk Cases:** 8
    - **Active Investigations:** {1 if st.session_state.investigation_mode else 0}
    """)
    
    # Execute selected page
    pages[selected_page]()

if __name__ == "__main__":
    main()
