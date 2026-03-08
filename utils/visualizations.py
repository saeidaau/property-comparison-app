import plotly.graph_objects as go
from typing import List, Dict

COMPARISON_COLORS = ["#FF0000", "#0000FF", "#00FF00", "#FF00FF", "#FFD700"]

STATIONS = {
    "asker": {"name": "Asker", "coords": (59.8344, 10.4355)},
    "sandvika": {"name": "Sandvika", "coords": (59.8893, 10.5221)}
}

def create_radar_chart(properties: List[Dict], title: str):
    categories = ['Byggeår', 'Station Dist', 'Area Brai', 'Tomt', 
                 'Bedrooms', 'Energy', 'Price Deal', 'Family']
    
    fig = go.Figure()
    
    for idx, prop in enumerate(properties):
        breakdown = prop.get('score_breakdown', {})
        values = [breakdown.get(cat, 50) for cat in categories]
        values.append(values[0])  # Close the loop
        
        short_addr = prop.get('address', '?').split(',')[0][:30]
        score = prop.get('score', 0)
        color = COMPARISON_COLORS[idx % len(COMPARISON_COLORS)]
        
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories + [categories[0]],
            fill='toself',
            name=f"{short_addr} ({score})",
            line=dict(color=color, width=3),
            opacity=0.5
        ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100]),
            bgcolor="rgba(245,245,255,0.3)"
        ),
        title=dict(text=f"<b>{title}</b>", font=dict(size=18)),
        width=900,
        height=650,
        template="plotly_white"
    )
    
    return fig

def create_distance_map(prop: Dict, station: str):
    station_info = STATIONS.get(station, STATIONS['asker'])
    lat, lon = prop.get('lat'), prop.get('lon')
    st_lat, st_lon = station_info['coords']
    
    fig = go.Figure()
    
    # Line
    fig.add_trace(go.Scattermapbox(
        lat=[lat, st_lat],
        lon=[lon, st_lon],
        mode='lines',
        line=dict(width=3, color='#EF553B'),
        name=f"Distance: {prop.get('distance_to_station_m', 0):,.0f} m"
    ))
    
    # Property marker
    fig.add_trace(go.Scattermapbox(
        lat=[lat],
        lon=[lon],
        mode='markers+text',
        marker=dict(size=16, color='#636EFA'),
        text=[prop.get('address', '').split(',')[0]],
        textposition='top center',
        name='Property'
    ))
    
    # Station marker
    fig.add_trace(go.Scattermapbox(
        lat=[st_lat],
        lon=[st_lon],
        mode='markers+text',
        marker=dict(size=16, color='#00CC96', symbol='star'),
        text=[station_info['name']],
        textposition='top center',
        name=station_info['name']
    ))
    
    mid_lat = (lat + st_lat) / 2
    mid_lon = (lon + st_lon) / 2
    
    fig.update_layout(
        mapbox=dict(
            style='open-street-map',
            center=dict(lat=mid_lat, lon=mid_lon),
            zoom=12.5
        ),
        title=f"<b>Property → {station_info['name']}: {prop.get('distance_to_station_m', 0):,.0f}m</b>",
        width=850,
        height=550,
        margin=dict(l=0, r=0, t=40, b=0)
    )
    
    return fig

def create_comparison_charts(properties: List[Dict]):
    charts = []
    
    # Price comparison
    addresses = [p.get('address', '').split(',')[0][:20] for p in properties]
    prices = [p.get('price', 0) for p in properties]
    
    fig_price = go.Figure(data=[
        go.Bar(x=addresses, y=prices, marker_color=COMPARISON_COLORS[:len(properties)])
    ])
    fig_price.update_layout(
        title="Price Comparison",
        yaxis_title="Price (NOK)",
        template="plotly_white",
        height=400
    )
    charts.append(fig_price)
    
    # Price per m²
    price_m2 = [p.get('price_per_m2', 0) for p in properties]
    
    fig_m2 = go.Figure(data=[
        go.Bar(x=addresses, y=price_m2, marker_color=COMPARISON_COLORS[:len(properties)])
    ])
    fig_m2.update_layout(
        title="Price per m² Comparison",
        yaxis_title="NOK/m²",
        template="plotly_white",
        height=400
    )
    charts.append(fig_m2)
    
    return charts
