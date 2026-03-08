import streamlit as st
import re
from typing import List, Dict, Any
from utils.data_fetcher import analyze_property, extract_finn_code
from utils.visualizations import (
    create_radar_chart, 
    create_distance_map,
    create_comparison_charts
)

# Page config
st.set_page_config(
    page_title="Property Comparison Tool",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize session state
if 'properties' not in st.session_state:
    st.session_state.properties = []
if 'property_stations' not in st.session_state:
    st.session_state.property_stations = {}  # finn_code -> station mapping
if 'analyzed_data' not in st.session_state:
    st.session_state.analyzed_data = {}

# Navigation using query parameters (makes browser back button work!)
def get_current_page():
    
    try:
        params = st.query_params
        return params.get("page", "main")
    except:
        return "main"

def get_finn_code_from_url():
    
    try:
        params = st.query_params
        return params.get("finn", None)
    except:
        return None

def go_to_main():
    
    st.query_params.clear()

def go_to_detail(finn_code):
    
    st.query_params.page = "detail"
    st.query_params.finn = finn_code

def go_to_comparison():
    
    st.query_params.page = "comparison"

# ═══════════════════════════════════════════════════════════════════════
# MAIN PAGE
# ═══════════════════════════════════════════════════════════════════════
def main_page():
    st.title("🏠 Property Comparison Tool")
    st.markdown("Compare up to 5 properties from FINN.no")
    st.info("💡 Tip: You can share property detail and comparison pages via URL!")
    st.markdown("---")
    
    # Add property button
    col1, col2, col3 = st.columns([1, 1, 3])
    with col1:
        if st.button("➕ Add Property", disabled=len(st.session_state.properties) >= 5):
            st.session_state.properties.append("")
            st.rerun()
    
    with col2:
        st.caption(f"({len(st.session_state.properties)}/5 properties)")
    
    # Display properties
    if not st.session_state.properties:
        st.info("👆 Click 'Add Property' to start comparing properties")
    
    for idx, prop_url in enumerate(st.session_state.properties):
        with st.container():
            # Changed layout: [URL, Station, Analyze, Detail, Delete]
            col1, col2, col3, col4, col5 = st.columns([3, 1, 0.8, 0.8, 0.4])
            
            with col1:
                new_url = st.text_input(
                    f"FINN.no link {idx + 1}",
                    value=prop_url,
                    key=f"url_{idx}",
                    placeholder="https://www.finn.no/realestate/homes/ad.html?finnkode=...",
                    label_visibility="visible"
                )
                if new_url != prop_url:
                    st.session_state.properties[idx] = new_url
            
            finn_code = extract_finn_code(new_url) if new_url else None
            is_analyzed = finn_code and finn_code in st.session_state.analyzed_data
            
            # Station dropdown for this property
            with col2:
                # Add some vertical spacing to align with text input
                st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                station = st.selectbox(
                    "Station",
                    options=["asker", "sandvika"],
                    index=0,
                    key=f"station_{idx}",
                    label_visibility="collapsed"
                )
                if finn_code:
                    st.session_state.property_stations[finn_code] = station
            
            with col3:
                # Add vertical spacing to align buttons
                st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                if st.button("🔍 Analyze", key=f"analyze_{idx}", disabled=not finn_code):
                    with st.spinner(f"Analyzing property {idx + 1}..."):
                        try:
                            station = st.session_state.property_stations.get(finn_code, "asker")
                            data = analyze_property(finn_code, station)
                            st.session_state.analyzed_data[finn_code] = data
                            st.success("✅ Done!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
            
            with col4:
                # Add vertical spacing to align buttons
                st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                if st.button("📊 Detail", key=f"detail_{idx}", disabled=not is_analyzed):
                    go_to_detail(finn_code)
                    st.rerun()
            
            with col5:
                # Add vertical spacing to align buttons
                st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                if st.button("🗑️", key=f"delete_{idx}"):
                    st.session_state.properties.pop(idx)
                    if finn_code in st.session_state.property_stations:
                        del st.session_state.property_stations[finn_code]
                    st.rerun()
            
            # Show quick info if analyzed
            if is_analyzed:
                data = st.session_state.analyzed_data[finn_code]
                score = data.get('score', 0)
                address = data.get('address', 'Unknown')
                station_used = data.get('station', 'asker')
                
                # Color code based on score
                if score >= 70:
                    color = "🟢"
                elif score >= 50:
                    color = "🟡"
                else:
                    color = "🔴"
                
                st.caption(f"{color} {address[:50]} | Score: {score}/100 | Station: {station_used.title()}")
            
            st.markdown("---")
    
    # Comparison button
    analyzed_count = len([p for p in st.session_state.properties 
                         if extract_finn_code(p) in st.session_state.analyzed_data])
    
    if analyzed_count >= 2:
        st.markdown("### Ready to Compare")
        if st.button("📊 Compare All Properties", type="primary", use_container_width=True):
            go_to_comparison()
            st.rerun()
    elif analyzed_count == 1:
        st.info("ℹ️ Add and analyze at least one more property to enable comparison")
    elif st.session_state.properties:
        st.info("ℹ️ Analyze at least 2 properties to enable comparison")

# ═══════════════════════════════════════════════════════════════════════
# DETAIL PAGE
# ═══════════════════════════════════════════════════════════════════════
def detail_page():
    finn_code = get_finn_code_from_url()
    if not finn_code or finn_code not in st.session_state.analyzed_data:
        st.error("Property data not found")
        if st.button("← Back to Main"):
            go_to_main()
            st.rerun()
        return
    
    data = st.session_state.analyzed_data[finn_code]
    
    # Back button (browser back will also work now!)
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("← Back to Main", type="primary"):
            go_to_main()
            st.rerun()
    with col2:
        st.caption("💡 Tip: Browser back button now works!")
    
    st.title(f"📊 {data.get('address', 'Property Details')}")
    
    # Key metrics in columns
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Overall Score",
            value=f"{data.get('score', 0)}/100"
        )
    
    with col2:
        st.metric(
            label="Days on Market",
            value=data.get('days_on_market', 'N/A')
        )
    
    with col3:
        st.metric(
            label="🛏️ Bedrooms",
            value=data.get('bedrooms', 'N/A')
        )
    
    with col4:
        st.metric(
            label="🚪 Rooms",
            value=data.get('rooms', 'N/A')
        )
    
    st.markdown("---")
    
    # Second row
    col1, col2, col3 = st.columns(3)
    
    with col1:
        age = data.get('age', 'N/A')
        year = data.get('year', 'N/A')
        st.metric(
            label="🏗️ Age (Byggeår)",
            value=f"{age} years ({year})"
        )
    
    with col2:
        st.metric(
            label="🚉 Distance to Station",
            value=f"{data.get('distance_to_station_m', 0):,.0f} m"
        )
    
    with col3:
        price_diff_pct = data.get('price_diff_pct', 0)
        delta_color = "normal" if abs(price_diff_pct) < 5 else ("inverse" if price_diff_pct > 0 else "normal")
        st.metric(
            label="Price vs Area Avg",
            value=f"{abs(price_diff_pct):.1f}%",
            delta="Cheaper" if price_diff_pct < 0 else "More expensive",
            delta_color=delta_color
        )
    
    st.markdown("---")
    
    # Price comparison visualization
    st.subheader("💰 Price Comparison")
    price_per_m2 = data.get('price_per_m2', 0)
    area_avg = data.get('area_avg_adjusted', 0)
    
    if price_per_m2 and area_avg:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**This Property:** {price_per_m2:,.0f} NOK/m²")
            st.markdown(f"**Area Average:** {area_avg:,.0f} NOK/m²")
            
            if price_diff_pct < -10:
                st.success(f"✅ Great deal! {abs(price_diff_pct):.1f}% below average")
            elif price_diff_pct < -5:
                st.success(f"✅ Good deal! {abs(price_diff_pct):.1f}% below average")
            elif price_diff_pct < 5:
                st.info(f"ℹ️ Fair price ({abs(price_diff_pct):.1f}% from average)")
            elif price_diff_pct < 15:
                st.warning(f"⚠️ Slightly expensive ({price_diff_pct:.1f}% above average)")
            else:
                st.error(f"⚠️ Overpriced ({price_diff_pct:.1f}% above average)")
    
    st.markdown("---")
    
    # Distance map
    st.subheader("📍 Location")
    property_station = data.get('station', 'asker')
    map_fig = create_distance_map(data, property_station)
    if map_fig:
        st.plotly_chart(map_fig, use_container_width=True)
    
    # Individual radar chart
    st.subheader("📊 Score Breakdown")
    radar_fig = create_radar_chart([data], f"Score Analysis: {data.get('address', '')}")
    if radar_fig:
        st.plotly_chart(radar_fig, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════
# COMPARISON PAGE
# ═══════════════════════════════════════════════════════════════════════
def comparison_page():
    # Back button (browser back will also work now!)
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("← Back to Main", type="primary"):
            go_to_main()
            st.rerun()
    with col2:
        st.caption("💡 Tip: Browser back button now works!")
    
    st.title("📊 Property Comparison")
    
    # Get analyzed properties
    analyzed_props = []
    stations_used = set()
    for prop_url in st.session_state.properties:
        finn_code = extract_finn_code(prop_url)
        if finn_code and finn_code in st.session_state.analyzed_data:
            prop_data = st.session_state.analyzed_data[finn_code]
            analyzed_props.append(prop_data)
            stations_used.add(prop_data.get('station', 'asker'))
    
    if len(analyzed_props) < 2:
        st.warning("Need at least 2 analyzed properties for comparison")
        return
    
    # Show station info if mixed
    if len(stations_used) > 1:
        st.info(f"ℹ️ Properties use different stations: {', '.join(sorted(stations_used)).title()}")
    else:
        st.info(f"🚉 All properties compared to: {list(stations_used)[0].title()} Station")
    
    # Combined radar chart
    st.subheader("🎯 Overall Comparison")
    radar_fig = create_radar_chart(analyzed_props, "Property Comparison")
    if radar_fig:
        st.plotly_chart(radar_fig, use_container_width=True)
    
    st.markdown("---")
    
    # Comparison table
    st.subheader("📋 Detailed Comparison")
    
    comparison_charts = create_comparison_charts(analyzed_props)
    for chart in comparison_charts:
        st.plotly_chart(chart, use_container_width=True)
    
    st.markdown("---")
    
    # Summary table
    st.subheader("📊 Summary Table")
    
    for idx, prop in enumerate(analyzed_props, 1):
        with st.expander(f"{idx}. {prop.get('address', 'Unknown')[:50]} - Score: {prop.get('score', 0)}/100"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"**Price:** {prop.get('price', 0):,} NOK")
                st.markdown(f"**Area:** {prop.get('area', 0)} m²")
                st.markdown(f"**Price/m²:** {prop.get('price_per_m2', 0):,} NOK")
            
            with col2:
                st.markdown(f"**Bedrooms:** {prop.get('bedrooms', 'N/A')}")
                st.markdown(f"**Age:** {prop.get('age', 'N/A')} years")
                st.markdown(f"**Energy:** {prop.get('energy', 'N/A')}")
            
            with col3:
                st.markdown(f"**Station:** {prop.get('station', 'asker').title()}")
                st.markdown(f"**Distance:** {prop.get('distance_to_station_m', 0):,.0f} m")
                st.markdown(f"**Days on Market:** {prop.get('days_on_market', 'N/A')}")
                price_diff = prop.get('price_diff_pct', 0)
                diff_emoji = "✅" if price_diff < -5 else ("⚠️" if price_diff > 5 else "ℹ️")
                st.markdown(f"**vs Average:** {diff_emoji} {price_diff:+.1f}%")

# ═══════════════════════════════════════════════════════════════════════
# MAIN ROUTER (now uses URL query parameters!)
# ═══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    page = get_current_page()
    
    if page == 'detail':
        detail_page()
    elif page == 'comparison':
        comparison_page()
    else:
        main_page()
