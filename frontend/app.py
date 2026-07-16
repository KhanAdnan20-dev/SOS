import streamlit as st
import pydeck as pdk
import requests
import time
import json
import math
import pandas as pd
from streamlit_js_eval import get_geolocation

# ==============================================================================
# PAGE CONFIGURATION & RICH AESTHETICS
# ==============================================================================
st.set_page_config(
    page_title="AAIPSI: Autonomous Medical Dispatch Network",
    page_icon="🚑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for Premium Glassmorphism & High-Contrast UI
st.markdown("""
<style>
    /* Main container styling */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
    }
    
    /* Header typography */
    h1, h2, h3 {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        font-weight: 700;
        letter-spacing: -0.03em;
    }
    
    /* Glowing metric cards */
    .metric-card {
        background: linear-gradient(135deg, rgba(30, 35, 45, 0.85) 0%, rgba(20, 24, 32, 0.95) 100%);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 14px;
        padding: 1.2rem;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        backdrop-filter: blur(8px);
        margin-bottom: 1rem;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(255, 75, 75, 0.5);
    }
    .metric-label {
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #9ba1ad;
        margin-bottom: 0.3rem;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 800;
        color: #ffffff;
    }
    
    /* Urgency Badges */
    .badge-critical {
        background: linear-gradient(90deg, #ff3333 0%, #cc0000 100%);
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.8rem;
        display: inline-block;
        box-shadow: 0 0 12px rgba(255, 51, 51, 0.5);
    }
    .badge-high {
        background: linear-gradient(90deg, #ff8800 0%, #e65c00 100%);
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.8rem;
        display: inline-block;
        box-shadow: 0 0 12px rgba(255, 136, 0, 0.4);
    }
    .badge-medium {
        background: linear-gradient(90deg, #00cc66 0%, #00994d 100%);
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.8rem;
        display: inline-block;
    }
    .badge-low {
        background: linear-gradient(90deg, #0099ff 0%, #0066cc 100%);
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.8rem;
        display: inline-block;
    }

    /* Equipment Pills */
    .eq-pill {
        background-color: #1e232d;
        color: #00e6a8;
        border: 1px solid #00e6a8;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 600;
        display: inline-block;
        margin: 4px 6px 4px 0;
        box-shadow: 0 0 8px rgba(0, 230, 168, 0.15);
    }
    
    /* Console & Audit Box */
    .console-box {
        background-color: #0b0e14;
        padding: 16px;
        border-radius: 8px;
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        font-size: 13px;
        color: #00ff88;
        border-left: 4px solid #00ff88;
        margin-top: 12px;
        line-height: 1.5;
    }

    /* Tab headers styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1.5rem;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 8px 8px 0px 0px;
        gap: 2px;
        padding-top: 10px;
        padding-bottom: 10px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# STATE INITIALIZATION
# ==============================================================================
if "caller_coords" not in st.session_state:
    # Default to Mumbai (Bandra) matching MySQL hospital/ambulance data
    st.session_state.caller_coords = [72.8370, 19.0596]  # [Longitude, Latitude]
if "request_caller_gps" not in st.session_state:
    st.session_state.request_caller_gps = False
if "last_dispatch" not in st.session_state:
    st.session_state.last_dispatch = None
if "preset_transcript" not in st.session_state:
    st.session_state.preset_transcript = ""

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================
def distance_km(origin, destination):
    """Calculate distance in kilometers between [lon, lat] points using Haversine formula."""
    lon1, lat1, lon2, lat2 = map(math.radians, [origin[0], origin[1], destination[0], destination[1]])
    a = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))

def check_backend_health(url):
    """Verify if the FastAPI backend is online and reachable."""
    try:
        resp = requests.get(f"{url}/api/fleet", timeout=2)
        return resp.status_code == 200
    except requests.RequestException:
        return False

# ==============================================================================
# SIDEBAR: CLOUD CONTROL & LOCATION CONFIGURATION
# ==============================================================================
with st.sidebar:
    st.markdown("### 🛠️ AAIPSI Cloud Control")
    backend_url = st.text_input("FastAPI Backend Endpoint:", value="http://localhost:8000")
    backend_url = backend_url.rstrip("/")
    
    is_online = check_backend_health(backend_url)
    if is_online:
        st.markdown('**Backend Status:** <span style="color:#00e6a8; font-weight:bold;">🟢 Online & Connected</span>', unsafe_allow_html=True)
    else:
        st.markdown('**Backend Status:** <span style="color:#ff3333; font-weight:bold;">🔴 Offline / Unreachable</span>', unsafe_allow_html=True)
        st.caption("Ensure `python -m backend.app` is running on port 8000.")
    
    st.markdown("---")
    st.markdown("### 📍 Emergency Location Capture")
    
    if st.button("🌐 Capture Device GPS Location", use_container_width=True):
        st.session_state.request_caller_gps = True

    if st.session_state.request_caller_gps:
        gps = get_geolocation(component_key="caller_device_gps")
        if gps and gps.get("coords"):
            coords = gps["coords"]
            st.session_state.caller_coords = [coords["longitude"], coords["latitude"]]
            st.session_state.request_caller_gps = False
            st.success(f"Captured device coordinates: {coords['latitude']:.5f}, {coords['longitude']:.5f}")
        elif gps and gps.get("error"):
            st.session_state.request_caller_gps = False
            st.warning(f"GPS unavailable: {gps['error']['message']}")
        else:
            st.caption("⏳ Waiting for browser location permission...")

    with st.expander("📍 Manual Coordinate Override", expanded=True):
        st.caption("Default coordinates match Mumbai (Bandra / Western Suburbs network).")
        cur_lon, cur_lat = st.session_state.caller_coords
        manual_lat = st.number_input("Caller Latitude", value=cur_lat, format="%.6f", step=0.001)
        manual_lon = st.number_input("Caller Longitude", value=cur_lon, format="%.6f", step=0.001)
        if st.button("Update Coordinates", use_container_width=True):
            st.session_state.caller_coords = [manual_lon, manual_lat]
            st.success("Updated active emergency coordinates!")

    lon, lat = st.session_state.caller_coords
    st.info(f"**Active Location:**\nLat: `{lat:.5f}` | Lon: `{lon:.5f}`")
    
    st.markdown("---")
    st.markdown("#### ⚡ About AAIPSI Network")
    st.caption("Automated Agent for Intelligent Pre-hospital Triage & Systemic Intervention. Integrates Layer 1 Deterministic Rules & Layer 2 Neural LLM (Qwen-2.5-7B) for real-time fleet coordination.")

# ==============================================================================
# HEADER
# ==============================================================================
st.title("🚑 AAIPSI: Autonomous Medical Dispatch & Triage Network")
st.markdown("Real-time AI-powered emergency classification, resource matching, and live road geometry routing.")
st.markdown("---")

# ==============================================================================
# MAIN TABS
# ==============================================================================
tab_dispatch, tab_fleet, tab_hospitals, tab_history = st.tabs([
    "🚨 Autonomous Dispatch & Triage",
    "🚑 Fleet Live Telemetry",
    "🏥 Hospital Network Matrix",
    "📜 Active Dispatches Registry"
])

# ------------------------------------------------------------------------------
# TAB 1: AUTONOMOUS DISPATCH & TRIAGE
# ------------------------------------------------------------------------------
with tab_dispatch:
    col_input, col_map = st.columns([1, 1.1], gap="large")
    
    with col_input:
        st.markdown("### 1. Emergency Call Transcript & Triage")
        patient_name = st.text_input("Patient Identifier / Caller Name:", value="John Doe (Emergency Call)")
        
        # Presets for quick hackathon/demo testing
        st.markdown("**⚡ Quick Test Scenarios:**")
        preset_cols = st.columns(4)
        if preset_cols[0].button("💔 Cardiac", use_container_width=True):
            st.session_state.preset_transcript = "45-year-old male experiencing crushing chest pain radiating down the left arm, sweating heavily, shortness of breath, high blood pressure."
        if preset_cols[1].button("💥 Trauma", use_container_width=True):
            st.session_state.preset_transcript = "30-year-old female involved in high-speed road collision, severe blunt force trauma to chest and forehead laceration, bleeding heavily."
        if preset_cols[2].button("🧠 Stroke", use_container_width=True):
            st.session_state.preset_transcript = "62-year-old male suddenly unable to speak, right side facial droop and weakness in right arm, conscious but confused."
        if preset_cols[3].button("🫁 Asthma", use_container_width=True):
            st.session_state.preset_transcript = "24-year-old female experiencing severe acute asthma attack, extreme wheezing and gasping for air, rescue inhaler ineffective."
        
        default_transcript = st.session_state.preset_transcript if st.session_state.preset_transcript else "Patient is a 34-year-old male with severe chest pain and palpitations. Breathing rapidly, conscious but dizzy."
        user_input = st.text_area("Enter raw emergency transcript or symptom description:", value=default_transcript, height=140)
        
        dispatch_btn = st.button("🚨 Dispatch Autonomous Agent", type="primary", use_container_width=True)
        
        if dispatch_btn:
            if not is_online:
                st.error("❌ Cannot dispatch: FastAPI Backend is currently unreachable. Please verify server status in sidebar.")
            elif not user_input.strip():
                st.warning("⚠️ Please provide an emergency transcript before dispatching.")
            else:
                with st.spinner("🧠 AI Neural Engine analyzing symptoms & matching live fleet resources..."):
                    payload = {
                        "patient_name": patient_name,
                        "raw_transcript": user_input,
                        "user_latitude": st.session_state.caller_coords[1],
                        "user_longitude": st.session_state.caller_coords[0]
                    }
                    try:
                        resp = requests.post(f"{backend_url}/api/dispatch", json=payload, timeout=30)
                        if resp.status_code == 200:
                            st.session_state.last_dispatch = resp.json()
                            st.success(f"⚡ Dispatch Confirmed! Incident ID: `{st.session_state.last_dispatch['incident_id']}`")
                        else:
                            st.error(f"❌ Dispatch failed ({resp.status_code}): {resp.text}")
                    except requests.RequestException as exc:
                        st.error(f"❌ Connection error during dispatch: {exc}")

        # Display Assessment Results if available
        if st.session_state.last_dispatch:
            res = st.session_state.last_dispatch
            ai = res.get("ai_analysis", {})
            amb = res.get("ambulance", {})
            hosp = res.get("hospital", {})
            
            st.markdown("---")
            st.markdown("### 2. AI Assessment & Assigned Resources")
            
            # Urgency badge styling
            urgency = res.get("ai_urgency_tier", "MEDIUM")
            badge_class = "badge-medium"
            if urgency in ("CRITICAL", "High", "1"): badge_class = "badge-critical"
            elif urgency in ("HIGH", "Urgent", "2"): badge_class = "badge-high"
            elif urgency in ("LOW", "Non-Urgent", "4"): badge_class = "badge-low"
            
            m_col1, m_col2, m_col3 = st.columns(3)
            with m_col1:
                st.markdown(f'''
                <div class="metric-card">
                    <div class="metric-label">Urgency Tier</div>
                    <div class="{badge_class}">{urgency}</div>
                </div>
                ''', unsafe_allow_html=True)
            with m_col2:
                st.markdown(f'''
                <div class="metric-card">
                    <div class="metric-label">Medical Tag</div>
                    <div class="metric-value" style="font-size:1.4rem;">{res.get("ai_medical_tag", "general").upper()}</div>
                </div>
                ''', unsafe_allow_html=True)
            with m_col3:
                conf = ai.get("confidence", 0.92)
                st.markdown(f'''
                <div class="metric-card">
                    <div class="metric-label">Arrival ETA</div>
                    <div class="metric-value" style="color:#00e6a8;">~{res.get("estimated_arrival_mins", 5)} mins</div>
                </div>
                ''', unsafe_allow_html=True)

            # Assigned Unit and Hospital Box
            st.markdown("#### 🚑 Assigned Emergency Resources")
            res_col1, res_col2 = st.columns(2)
            with res_col1:
                st.info(f"**Assigned Ambulance:** `{amb.get('vehicle_number', 'N/A')}` (`{amb.get('ambulance_id')}`)\n\n"
                        f"**Tier:** {amb.get('tier', 'ALS')} · **Status:** EN ROUTE")
            with res_col2:
                st.success(f"**Target Hospital:** `{hosp.get('name', 'General Hospital')}`\n\n"
                           f"**ICU Beds Available:** {hosp.get('icu_beds_available', 'N/A')} · **OT Status:** {hosp.get('ot_status', 'AVAILABLE')}")

            # Equipment and First Aid
            suspected = ai.get("suspected_conditions", [])
            if suspected:
                st.markdown("**🔍 Suspected Conditions:** " + ", ".join([f"`{c}`" for c in suspected]))
            
            eq_list = ai.get("first_aid", ["Standard ALS Trauma Kit", "Oxygen Support", "Vital Signs Monitor"])
            if not eq_list: eq_list = ["Standard ALS Kit", "Oxygen", "Defibrillator", "IV Fluids"]
            st.markdown("**🎒 Required Equipment & First Aid Instructions:**")
            eq_html = "".join([f'<span class="eq-pill">⚡ {item}</span>' for item in eq_list])
            st.markdown(eq_html, unsafe_allow_html=True)
            
            reasoning = ai.get("reasoning") or res.get("message", "Processed successfully by autonomous dispatch network.")
            st.markdown(f'<div class="console-box"><b>Audit & Reasoning Log:</b><br>{reasoning}</div>', unsafe_allow_html=True)

    with col_map:
        st.markdown("### 🗺️ Live Tactical Road Geometry & Tracking")
        
        # Determine center and layers for PyDeck
        caller_lon, caller_lat = st.session_state.caller_coords
        
        if st.session_state.last_dispatch:
            res = st.session_state.last_dispatch
            amb = res.get("ambulance", {})
            raw_route_pts = res.get("route_points", [])
            route_pts = [[pt[1], pt[0]] if len(pt) >= 2 and pt[0] < 40 else pt for pt in raw_route_pts]
            raw_route_hosp_pts = res.get("route_to_hospital_points", [])
            route_hosp_pts = [[pt[1], pt[0]] if len(pt) >= 2 and pt[0] < 40 else pt for pt in raw_route_hosp_pts]
            amb_id = amb.get("ambulance_id", "")
            
            hosp_pos = [hosp.get("longitude", caller_lon - 0.02), hosp.get("latitude", caller_lat - 0.02)]
            
            # Live Simulation and Telemetry Controls
            st.markdown("#### 📡 Real-Time Autonomous Tracking & Live GPS Sync")
            watch_live = st.toggle("▶️ Enable Live Simulation Telemetry Loop (`MySQL` / `Simulator Sync`)", value=True)
            
            telemetry_placeholder = st.empty()
            map_placeholder = st.empty()
            
            if watch_live and amb_id:
                # 1. Pre-Run Dynamic Line Tracing Animation on the Map (`Corridor Calculation Phase`)
                if route_pts and len(route_pts) > 1:
                    with telemetry_placeholder.container():
                        st.info("⚡ CALCULATING OPTIMAL OSRM ROAD CORRIDOR... TRACING SHORTEST TRAFFIC-AWARE PATH")
                    step_inc = max(1, len(route_pts) // 15)
                    for k in range(2, len(route_pts) + step_inc, step_inc):
                        slice_idx = min(len(route_pts), k)
                        traced_path = route_pts[:slice_idx]
                        
                        layer_caller_c = pdk.Layer("ScatterplotLayer", data=[{"pos": [caller_lon, caller_lat]}], get_position="pos", get_fill_color=[255, 45, 85, 240], get_radius=80, radius_min_pixels=6, radius_max_pixels=14)
                        layer_caller_b = pdk.Layer("TextLayer", data=[{"pos": [caller_lon, caller_lat], "text": "🆘"}], get_position="pos", get_text="text", get_size=24)
                        layer_hosp_c = pdk.Layer("ScatterplotLayer", data=[{"pos": hosp_pos}], get_position="pos", get_fill_color=[0, 153, 255, 240], get_radius=90, radius_min_pixels=7, radius_max_pixels=15)
                        layer_hosp_b = pdk.Layer("TextLayer", data=[{"pos": hosp_pos, "text": "🏥"}], get_position="pos", get_text="text", get_size=24)
                        layer_amb_c = pdk.Layer("ScatterplotLayer", data=[{"pos": route_pts[0]}], get_position="pos", get_fill_color=[255, 193, 7, 255], get_radius=100, radius_min_pixels=8, radius_max_pixels=16)
                        layer_amb_b = pdk.Layer("TextLayer", data=[{"pos": route_pts[0], "text": "🚑"}], get_position="pos", get_text="text", get_size=26)
                        layer_trace = pdk.Layer("PathLayer", data=[{"path": traced_path}], get_path="path", get_color=[255, 140, 0, 240], width_scale=25, width_min_pixels=3)
                        
                        map_placeholder.pydeck_chart(pdk.Deck(
                            layers=[layer_trace, layer_caller_c, layer_caller_b, layer_hosp_c, layer_hosp_b, layer_amb_c, layer_amb_b],
                            initial_view_state=pdk.ViewState(latitude=caller_lat, longitude=caller_lon, zoom=12.5, pitch=45),
                            map_style="dark"
                        ))
                        time.sleep(0.08)
                    with telemetry_placeholder.container():
                        st.success("🔒 OSRM ROAD CORRIDOR LOCKED — LAUNCHING EMERGENCY UNIT")
                    time.sleep(0.5)

                # Automated Live Polling & Animation Loop synchronized with backend simulator (`simulate_movement`)
                # Automated Live Polling & Animation Loop synchronized with backend simulator (`simulate_movement`)
                max_polls = 200  # Safety bound (`~5 minutes` at 1.5s tick rate)
                prev_lon, prev_lat = caller_lon, caller_lat
                initial_dist_to_patient = max(0.1, distance_km([route_pts[0][0], route_pts[0][1]], [caller_lon, caller_lat])) if route_pts else 1.0
                initial_dist_to_hosp = max(0.1, distance_km([caller_lon, caller_lat], [hosp_pos[0], hosp_pos[1]]))
                
                for step in range(max_polls):
                    try:
                        # Pull latest live coordinates directly from MySQL / Backend API
                        amb_data = requests.get(f"{backend_url}/api/fleet/{amb_id}", timeout=4).json()
                        cur_lon = amb_data.get("amb_longitude", amb.get("amb_longitude", caller_lon))
                        cur_lat = amb_data.get("amb_latitude", amb.get("amb_latitude", caller_lat))
                        cur_status = amb_data.get("status", "DISPATCHED")
                    except Exception:
                        cur_lon = amb.get("amb_longitude", caller_lon)
                        cur_lat = amb.get("amb_latitude", caller_lat)
                        cur_status = "EN_ROUTE_TO_PATIENT"
                    
                    # Calculate true physical distances right now
                    dist_to_caller = distance_km([cur_lon, cur_lat], [caller_lon, caller_lat])
                    dist_to_hosp = distance_km([cur_lon, cur_lat], [hosp_pos[0], hosp_pos[1]])
                    
                    # Calculate road bearing/heading so vehicle icon rotates along every twist and turn
                    d_lon = cur_lon - prev_lon
                    d_lat = cur_lat - prev_lat
                    if abs(d_lon) > 0.00001 or abs(d_lat) > 0.00001:
                        heading = (math.degrees(math.atan2(d_lon, d_lat)) + 360) % 360
                        prev_lon, prev_lat = cur_lon, cur_lat
                    else:
                        heading = amb_data.get("heading", 0)
                        
                    sim_speed = round(38.0 + (math.sin(step) * 12.0), 1) if cur_status != "AVAILABLE" else 0.0

                    # 1. Determine Phase right from exact status and physical distance
                    if cur_status == "AT_SCENE" or (cur_status in ["DISPATCHED", "EN_ROUTE_TO_PATIENT"] and dist_to_caller <= 0.06):
                        # At Scene stabilizing patient
                        target_lon, target_lat = caller_lon, caller_lat
                        phase_label = "🛑 ON SCENE: PARAMEDICS STABILIZING & LOADING PATIENT"
                        amb_color = [255, 45, 85, 255]       # Pulsing Crimson/White
                        amb_badge = "🛑"
                        show_patient = True                  # Patient stays visible on scene during boarding!
                        progress_pct = 0.50
                        path1_color = [255, 140, 0, 240]
                        path2_color = [0, 255, 180, 240]
                    elif cur_status in ["EN_ROUTE_TO_HOSPITAL"] or (dist_to_caller <= 0.06 and step > 8 and cur_status != "EN_ROUTE_TO_PATIENT"):
                        # Phase 2: Heading to Hospital
                        target_lon, target_lat = hosp_pos[0], hosp_pos[1]
                        phase_label = f"🚨 PHASE 2: CRITICAL ICU LIFE SUPPORT IN TRANSIT -> {hosp.get('name', 'HOSPITAL').upper()}"
                        amb_color = [0, 230, 168, 255]       # Bright Medical Cyan / Emerald ICU
                        amb_badge = "🚨"
                        show_patient = False                 # Patient safely boarded inside transport bay!
                        progress_pct = min(0.97, 0.52 + 0.45 * (1.0 - min(1.0, dist_to_hosp / initial_dist_to_hosp)))
                        path1_color = [110, 115, 125, 90]    # Faded completed rescue leg
                        path2_color = [0, 255, 180, 245]     # Active transfer corridor
                    else:
                        # Phase 1: En Route to Patient
                        target_lon, target_lat = caller_lon, caller_lat
                        phase_label = "🚑 PHASE 1: RESPONDING TO SCENE (EN ROUTE TO PATIENT)"
                        amb_color = [255, 193, 7, 255]       # Flashing Emergency Amber
                        amb_badge = "🚑"
                        show_patient = True                  # Patient tracking symbol stays visible 100% of the way!
                        progress_pct = min(0.48, max(0.02, 0.48 * (1.0 - min(1.0, dist_to_caller / initial_dist_to_patient))))
                        path1_color = [255, 140, 0, 240]     # High-intensity Tactical Orange
                        path2_color = [0, 230, 168, 150]     # Preview Clinical Cyan Transfer Corridor

                    # 2. Check Mission Completion Finishing Symbol (`Hospital Handover` at ER)
                    # Only complete when physically at hospital (`dist_to_hosp <= 0.06` during Phase 2) or released!
                    if (cur_status == "AVAILABLE" and step > 10) or (step > 15 and dist_to_hosp <= 0.06 and not show_patient) or step > max_polls - 2:
                        with telemetry_placeholder.container():
                            st.success(f"🏁 MISSION ACCOMPLISHED — PATIENT SAFELY TRANSFERRED TO ICU TRAUMA BAY (`{hosp.get('name')}`) | UNIT RELEASED TO STANDBY")
                        
                        layer_finish_aura = pdk.Layer(
                            "ScatterplotLayer",
                            data=[{"pos": hosp_pos, "name": "Handover Bay"}],
                            get_position="pos", get_fill_color=[0, 255, 128, 240],
                            get_radius=220, radius_min_pixels=15, radius_max_pixels=30, pickable=True
                        )
                        layer_finish_badge = pdk.Layer(
                            "TextLayer",
                            data=[{"pos": hosp_pos, "text": "🏁", "name": "Mission Complete"}],
                            get_position="pos", get_text="text", get_size=32, get_color=[255, 255, 255, 255],
                            get_alignment_baseline="'center'", pickable=True
                        )
                        layer_hosp_circle = pdk.Layer(
                            "ScatterplotLayer",
                            data=[{"pos": hosp_pos, "name": hosp.get("name", "Hospital ER")}],
                            get_position="pos", get_fill_color=[0, 153, 255, 240],
                            get_radius=90, radius_min_pixels=7, radius_max_pixels=15, pickable=True
                        )
                        layer_hosp_badge = pdk.Layer("TextLayer", data=[{"pos": hosp_pos, "text": "🏥"}], get_position="pos", get_text="text", get_size=24)
                        
                        finish_layers = [layer_finish_aura, layer_hosp_circle, layer_hosp_badge, layer_finish_badge]
                        if route_hosp_pts:
                            finish_layers.insert(0, pdk.Layer("PathLayer", data=[{"path": route_hosp_pts}], get_path="path", get_color=[0, 255, 180, 245], width_scale=22))
                        
                        map_placeholder.pydeck_chart(pdk.Deck(
                            layers=finish_layers,
                            initial_view_state=pdk.ViewState(latitude=hosp_pos[1], longitude=hosp_pos[0], zoom=13.5, pitch=55),
                            map_style="dark"
                        ))
                        break
                    
                    # Trace live remaining distance using Haversine formula
                    dist_rem_km = distance_km([cur_lon, cur_lat], [target_lon, target_lat])
                    eta_est_mins = max(1, int((dist_rem_km / max(1.0, sim_speed)) * 60)) if sim_speed > 0 else 0
                    
                    # Render live telemetry cards inside placeholder
                    with telemetry_placeholder.container():
                        t_col1, t_col2, t_col3, t_col4 = st.columns(4)
                        t_col1.metric("Live GPS Speed", f"{sim_speed} km/h", f"State: {cur_status}")
                        t_col2.metric("Tactical Clinical State", phase_label)
                        t_col3.metric("Distance to Target", f"{dist_rem_km:.2f} km", f"~{eta_est_mins} mins remaining" if sim_speed > 0 else "Arrived at target")
                        t_col4.metric("Live GPS / Bearing", f"{cur_lat:.4f}, {cur_lon:.4f} ({int(heading)}°)")
                        st.progress(progress_pct, text=f"🚀 Mission Progress: {int(progress_pct * 100)}% (`{amb.get('vehicle_number')}` -> `{hosp.get('name')}`)")
                    
                    # Build PyDeck Layers with Literal Emoji Badges (`TextLayer`) & Dual-Corridor Polylines (`PathLayer`)
                    layer_caller_circle = pdk.Layer(
                        "ScatterplotLayer",
                        data=[{"pos": [caller_lon, caller_lat], "name": "Emergency Scene"}],
                        get_position="pos", get_fill_color=[255, 45, 85, 240],
                        get_radius=80, radius_min_pixels=6, radius_max_pixels=14, pickable=True
                    )
                    layer_caller_badge = pdk.Layer(
                        "TextLayer",
                        data=[{"pos": [caller_lon, caller_lat], "text": "🆘", "name": "Emergency Caller"}],
                        get_position="pos", get_text="text", get_size=24, get_color=[255, 255, 255, 255],
                        get_alignment_baseline="'center'", pickable=True
                    )
                    
                    layer_hosp_circle = pdk.Layer(
                        "ScatterplotLayer",
                        data=[{"pos": hosp_pos, "name": hosp.get("name", "Hospital ER")}],
                        get_position="pos", get_fill_color=[0, 153, 255, 240],
                        get_radius=90, radius_min_pixels=7, radius_max_pixels=15, pickable=True
                    )
                    layer_hosp_badge = pdk.Layer(
                        "TextLayer",
                        data=[{"pos": hosp_pos, "text": "🏥", "name": hosp.get("name", "Hospital ER")}],
                        get_position="pos", get_text="text", get_size=24, get_color=[255, 255, 255, 255],
                        get_alignment_baseline="'center'", pickable=True
                    )
                    
                    layer_amb_circle = pdk.Layer(
                        "ScatterplotLayer",
                        data=[{"pos": [cur_lon, cur_lat], "name": f"Live Unit: {amb.get('vehicle_number')}"}],
                        get_position="pos", get_fill_color=amb_color,
                        get_radius=100, radius_min_pixels=8, radius_max_pixels=16, pickable=True
                    )
                    layer_amb_badge = pdk.Layer(
                        "TextLayer",
                        data=[{"pos": [cur_lon, cur_lat], "text": amb_badge, "name": f"Unit: {amb.get('vehicle_number')}", "angle": heading}],
                        get_position="pos", get_text="text", get_size=26, get_color=[255, 255, 255, 255],
                        get_angle="angle", get_alignment_baseline="'center'", pickable=True
                    )
                    
                    # If patient is not yet boarded (`show_patient == True`), show scene circle & emoji; once boarded (`False`), vanish them!
                    if show_patient:
                        layers = [layer_caller_circle, layer_caller_badge, layer_hosp_circle, layer_hosp_badge, layer_amb_circle, layer_amb_badge]
                    else:
                        layers = [layer_hosp_circle, layer_hosp_badge, layer_amb_circle, layer_amb_badge]
                    
                    # Dual-Corridor Simultaneous Tracing (Pre-Pickup Orange + Transfer Cyan)
                    if route_hosp_pts and len(route_hosp_pts) > 1:
                        layer_path_transfer = pdk.Layer(
                            "PathLayer",
                            data=[{"path": route_hosp_pts, "name": "Phase 2: Hospital Transfer Corridor"}],
                            get_path="path", get_color=path2_color,
                            width_scale=22, width_min_pixels=3, pickable=True
                        )
                        layers.insert(0, layer_path_transfer)
                        
                    if route_pts and len(route_pts) > 1:
                        layer_path_pickup = pdk.Layer(
                            "PathLayer",
                            data=[{"path": route_pts, "name": "Phase 1: Emergency Scene Trajectory"}],
                            get_path="path", get_color=path1_color,
                            width_scale=25, width_min_pixels=3, pickable=True
                        )
                        layers.insert(0, layer_path_pickup)
                    
                    # Camera tracks live ambulance movement smoothly
                    dynamic_view = pdk.ViewState(
                        latitude=cur_lat,
                        longitude=cur_lon,
                        zoom=13.0,
                        pitch=50,
                        bearing=0
                    )
                    
                    map_placeholder.pydeck_chart(pdk.Deck(
                        layers=layers,
                        initial_view_state=dynamic_view,
                        map_style="dark",
                        tooltip={"text": "{name}"}
                    ))
                    
                    # Check if mission completed (backend simulator released unit back to AVAILABLE)
                    if cur_status == "AVAILABLE" and step > 4:
                        break
                        
                    time.sleep(1.5)
            else:
                # Static snapshot view when live toggle is off
                amb_pos = [amb.get("amb_longitude", caller_lon + 0.02), amb.get("amb_latitude", caller_lat + 0.02)]
                layer_caller = pdk.Layer("ScatterplotLayer", data=[{"pos": [caller_lon, caller_lat], "name": "Caller"}], get_position="pos", get_fill_color=[255, 45, 85, 240], get_radius=80, radius_min_pixels=6, radius_max_pixels=14)
                layer_caller_b = pdk.Layer("TextLayer", data=[{"pos": [caller_lon, caller_lat], "text": "🆘"}], get_position="pos", get_text="text", get_size=24)
                layer_hosp = pdk.Layer("ScatterplotLayer", data=[{"pos": hosp_pos, "name": hosp.get("name", "Hospital")}], get_position="pos", get_fill_color=[0, 153, 255, 240], get_radius=90, radius_min_pixels=7, radius_max_pixels=15)
                layer_hosp_b = pdk.Layer("TextLayer", data=[{"pos": hosp_pos, "text": "🏥"}], get_position="pos", get_text="text", get_size=24)
                layer_amb = pdk.Layer("ScatterplotLayer", data=[{"pos": amb_pos, "name": amb.get("vehicle_number", "Ambulance")}], get_position="pos", get_fill_color=[255, 193, 7, 255], get_radius=100, radius_min_pixels=8, radius_max_pixels=16)
                layer_amb_b = pdk.Layer("TextLayer", data=[{"pos": amb_pos, "text": "🚑"}], get_position="pos", get_text="text", get_size=26)
                layers = [layer_caller, layer_caller_b, layer_hosp, layer_hosp_b, layer_amb, layer_amb_b]
                if route_hosp_pts:
                    layers.insert(0, pdk.Layer("PathLayer", data=[{"path": route_hosp_pts}], get_path="path", get_color=[0, 230, 168, 160], width_scale=22))
                if route_pts:
                    layers.insert(0, pdk.Layer("PathLayer", data=[{"path": route_pts}], get_path="path", get_color=[255, 140, 0, 240], width_scale=25))
                map_placeholder.pydeck_chart(pdk.Deck(layers=layers, initial_view_state=pdk.ViewState(latitude=caller_lat, longitude=caller_lon, zoom=12.5, pitch=45), map_style="dark"))
        else:
            # Default map view before dispatch
            layer_caller = pdk.Layer(
                "ScatterplotLayer",
                data=[{"pos": [caller_lon, caller_lat], "name": "Emergency Location"}],
                get_position="pos",
                get_fill_color=[255, 45, 85, 240],
                get_radius=90,
                radius_min_pixels=6,
                radius_max_pixels=14,
                pickable=True
            )
            view_state = pdk.ViewState(
                latitude=caller_lat,
                longitude=caller_lon,
                zoom=12,
                pitch=30,
                bearing=0
            )
            st.pydeck_chart(pdk.Deck(
                layers=[layer_caller],
                initial_view_state=view_state,
                map_style="dark",
                tooltip={"text": "{name}"}
            ))
            st.caption("Enter a transcript on the left and click **Dispatch Autonomous Agent** to generate live routing and allocate resources.")

# ------------------------------------------------------------------------------
# TAB 2: FLEET LIVE TELEMETRY
# ------------------------------------------------------------------------------
with tab_fleet:
    st.markdown("### 🚑 Live Emergency Fleet Matrix (`GET /api/fleet`)")
    if not is_online:
        st.error("Backend is unreachable. Connect to view live fleet telemetry.")
    else:
        try:
            fleet_data = requests.get(f"{backend_url}/api/fleet", timeout=5).json()
            if fleet_data:
                total_units = len(fleet_data)
                avail_units = sum(1 for u in fleet_data if u["status"] == "AVAILABLE")
                disp_units = total_units - avail_units
                
                f_col1, f_col2, f_col3 = st.columns(3)
                f_col1.metric("Total Fleet Units", f"{total_units} Vehicles")
                f_col2.metric("Available / Standby", f"{avail_units} Units", delta=f"{avail_units/total_units*100:.0f}% ready")
                f_col3.metric("Currently Dispatched", f"{disp_units} Units")
                
                # Render 3D Fleet Map
                st.markdown("#### 🌐 Real-Time Fleet Geographic Distribution")
                map_data_avail = [{"pos": [u["amb_longitude"], u["amb_latitude"]], "name": f"{u['vehicle_number']} ({u['tier']}) - AVAILABLE"} for u in fleet_data if u["status"] == "AVAILABLE"]
                map_data_disp = [{"pos": [u["amb_longitude"], u["amb_latitude"]], "name": f"{u['vehicle_number']} ({u['tier']}) - DISPATCHED"} for u in fleet_data if u["status"] != "AVAILABLE"]
                
                l_avail = pdk.Layer(
                    "ScatterplotLayer",
                    data=map_data_avail,
                    get_position="pos",
                    get_fill_color=[0, 230, 168, 255],      # Semantic: Medic Green (Ready)
                    get_radius=85,
                    radius_min_pixels=6,
                    radius_max_pixels=14,
                    pickable=True
                )
                l_disp = pdk.Layer(
                    "ScatterplotLayer",
                    data=map_data_disp,
                    get_position="pos",
                    get_fill_color=[255, 193, 7, 255],      # Semantic: Emergency Amber (Active)
                    get_radius=90,
                    radius_min_pixels=7,
                    radius_max_pixels=15,
                    pickable=True
                )
                st.pydeck_chart(pdk.Deck(
                    layers=[l_avail, l_disp],
                    initial_view_state=pdk.ViewState(latitude=19.0596, longitude=72.8370, zoom=12, pitch=35),
                    map_style="dark",
                    tooltip={"text": "{name}"}
                ))
                
                st.markdown("#### 📋 Fleet Roster Detail")
                df_fleet = pd.DataFrame(fleet_data)
                df_fleet = df_fleet[["ambulance_id", "vehicle_number", "tier", "status", "amb_latitude", "amb_longitude"]]
                df_fleet.columns = ["Unit ID", "Vehicle Registration", "Service Tier", "Current Status", "Latitude", "Longitude"]
                st.dataframe(df_fleet, use_container_width=True, hide_index=True)
            else:
                st.info("No ambulances found in database.")
        except Exception as exc:
            st.error(f"Error fetching fleet data: {exc}")

# ------------------------------------------------------------------------------
# TAB 3: HOSPITAL NETWORK MATRIX
# ------------------------------------------------------------------------------
with tab_hospitals:
    st.markdown("### 🏥 Connected Trauma & Hospital Network (`GET /api/hospitals`)")
    if not is_online:
        st.error("Backend is unreachable. Connect to view hospital matrix.")
    else:
        try:
            hosp_data = requests.get(f"{backend_url}/api/hospitals", timeout=5).json()
            if hosp_data:
                total_hosp = len(hosp_data)
                total_icu = sum(h["icu_beds_available"] for h in hosp_data)
                div_hosp = sum(1 for h in hosp_data if h["ot_status"] == "UNAVAILABLE")
                
                h_col1, h_col2, h_col3 = st.columns(3)
                h_col1.metric("Connected Medical Centers", f"{total_hosp} Hospitals")
                h_col2.metric("Total Available ICU Beds", f"{total_icu} Beds")
                h_col3.metric("Hospitals on OT Diversion", f"{div_hosp} Centers", delta="- diversion active" if div_hosp > 0 else "All clear", delta_color="inverse")
                
                # Render Hospital Map
                st.markdown("#### 🗺️ Medical Centers Geographic Distribution")
                map_data_h = [{"pos": [h["longitude"], h["latitude"]], "name": f"{h['name']} ({h['icu_beds_available']} ICU Beds)"} for h in hosp_data]
                l_hosp = pdk.Layer(
                    "ScatterplotLayer",
                    data=map_data_h,
                    get_position="pos",
                    get_fill_color=[0, 153, 255, 230],       # Semantic: Clinical ER Medical Blue
                    get_radius=90,
                    radius_min_pixels=7,
                    radius_max_pixels=15,
                    pickable=True
                )
                st.pydeck_chart(pdk.Deck(
                    layers=[l_hosp],
                    initial_view_state=pdk.ViewState(latitude=19.0596, longitude=72.8370, zoom=12, pitch=35),
                    map_style="dark",
                    tooltip={"text": "{name}"}
                ))
                
                st.markdown("#### 🏥 Facility Capacity & Specialization Matrix")
                df_hosp = pd.DataFrame(hosp_data)
                df_hosp = df_hosp[["hospital_id", "name", "icu_beds_available", "ot_status", "specialty_tags", "latitude", "longitude"]]
                df_hosp.columns = ["Hospital ID", "Facility Name", "Available ICU Beds", "OT Status", "Trauma Specialties", "Latitude", "Longitude"]
                st.dataframe(df_hosp, use_container_width=True, hide_index=True)
            else:
                st.info("No hospitals found in database.")
        except Exception as exc:
            st.error(f"Error fetching hospital matrix: {exc}")

# ------------------------------------------------------------------------------
# TAB 4: ACTIVE DISPATCHES LOG
# ------------------------------------------------------------------------------
with tab_history:
    st.markdown("### 📜 System Dispatch History & Audit Log (`GET /api/dispatches`)")
    if not is_online:
        st.error("Backend is unreachable. Connect to view active dispatches.")
    else:
        if st.button("🔄 Refresh History Log", use_container_width=False):
            st.rerun()
        try:
            history_data = requests.get(f"{backend_url}/api/dispatches", timeout=5).json()
            if history_data:
                df_hist = pd.DataFrame(history_data)
                st.dataframe(df_hist, use_container_width=True, hide_index=True)
            else:
                st.info("No active dispatches logged in system history yet. Run a dispatch from Tab 1!")
        except Exception as exc:
            st.error(f"Error fetching dispatches: {exc}")
