import re
import json
import requests
import requests_cache
from datetime import date
import math
import html as _html

# Setup caching
requests_cache.install_cache('property_cache', backend='memory', expire_after=3600)

# Configuration
EP = {
    "addr": "https://ws.geonorge.no/adresser/v1/sok",
    "wfs": "https://wfs.geonorge.no/skwms1/wfs.matrikkelen-eiendomskart",
    "finn_ad": "https://www.finn.no/realestate/homes/ad.html?finnkode={fk}",
}

STATIONS = {
    "asker": {
        "name": "Asker",
        "coords": (59.8344, 10.4355),
    },
    "sandvika": {
        "name": "Sandvika",
        "coords": (59.8893, 10.5221),
    }
}

AREA_FACTORS = {
    "heggedal": 0.75, "vakås": 0.80, "vollen": 0.85,
    "asker sentrum": 1.00, "borgen": 0.95, "drengsrud": 0.90,
    "dikemark": 0.88, "holmen": 0.92, "østenstad": 0.87,
    "vardåsen": 0.93, "sandvika": 1.00, "kadettangen": 0.95,
}

def _haversine(lat1, lon1, lat2, lon2):
    R = 6_371_000
    p = math.pi / 180
    a = (math.sin((lat2-lat1)*p/2)**2 + 
         math.cos(lat1*p)*math.cos(lat2*p)*math.sin((lon2-lon1)*p/2)**2)
    return 2*R*math.asin(math.sqrt(a))

def extract_finn_code(url_or_code):
    if not url_or_code:
        return None
    s = str(url_or_code).strip()
    if "finnkode=" in s:
        s = s.split("finnkode=")[1].split("&")[0]
    s = re.sub(r"[^\d]", "", s)
    return s if len(s) >= 6 else None

def geocode(address):
    addr = " ".join(address.split()).strip()
    r = requests.get(EP["addr"], params={"sok": addr, "treffPerSide": 1, "utkoordsys": 4326}, timeout=10)
    hits = r.json().get("adresser", [])
    if not hits:
        return None
    b = hits[0]
    rp = b.get("representasjonspunkt", {})
    return {
        "formatted": b.get("adressetekst", addr),
        "lat": rp.get("lat"),
        "lon": rp.get("lon"),
    }

def get_finn_data(finn_code):
    url = EP["finn_ad"].format(fk=finn_code)
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers, timeout=15)
    txt = r.text
    
    def _m(pattern, group=1):
        hit = re.search(pattern, txt, re.IGNORECASE | re.DOTALL)
        return _html.unescape(hit.group(group).strip()) if hit else None
    
    def _clean_price(val):
        if not val:
            return None
        val = val.replace(" ", "").replace("\xa0", "").replace(",-", "")
        return int(val) if val.isdigit() else None
    
    # Extract address - try multiple patterns
    address = None
    
    # Pattern 1: class="pl-4" address format (MOST RELIABLE)
    addr_match = re.search(r'address"[^>]*class="pl-4">([^<]+)<', txt)
    if addr_match:
        address = _html.unescape(addr_match.group(1).strip())
    
    # Pattern 2: Norwegian address pattern (WORKS WELL)
    if not address:
        addr_match = re.search(r'([A-ZÆØÅ][a-zæøå]+(?:\s+[a-zæøå]+)*\s+\d+[A-Z]?),?\s*(\d{4})\s+([A-ZÆØÅ][a-zæøå]+)', txt)
        if addr_match:
            street = addr_match.group(1)
            postcode = addr_match.group(2)
            city = addr_match.group(3)
            address = f"{street}, {postcode} {city}"
    
    # Pattern 3: address-text class (fallback)
    if not address:
        addr_match = re.search(r'address-text[^>]*>([^<]+)<', txt)
        if addr_match:
            address = _html.unescape(addr_match.group(1).strip())
    
    # Pattern 4: streetAddress JSON (fallback)
    if not address:
        addr_match = re.search(r'"streetAddress"\s*:\s*"([^"]+)"', txt)
        if addr_match:
            address = addr_match.group(1).strip()
    
    # Extract data
    data = {
        "address": address,
        "title": _m(r'<title>([^<]+)</title>'),
        "price": _clean_price(_m(r'Prisantydning.*?([\d\s\xa0]+)\s*kr')),
        "area": int(_m(r'info-usable-i-area.*?>(\d+)\s*m') or 0),
        "bedrooms": int(_m(r'info-bedrooms.*?>(\d+)') or 0),
        "rooms": int(_m(r'info-rooms.*?>(\d+)') or 0),
        "year": int(_m(r'info-construction-year.*?>(\d{4})') or 0),
        "energy": _m(r'energy-label-info.*?>([A-G])'),
        "tomt": int(_m(r'info-plot-area.*?>(\d+)\s*m') or 0),
    }
    
    # Days on market
    pub_date = _m(r'[Pp]ublisert.*?(\d{1,2}\.\s?\w+\.?\s?\d{4})')
    if pub_date:
        months = {"jan":1,"feb":2,"mar":3,"apr":4,"mai":5,"jun":6,
                 "jul":7,"aug":8,"sep":9,"okt":10,"nov":11,"des":12}
        m = re.match(r"(\d{1,2})\.?\s*(\w+)\.?\s*(\d{4})", pub_date)
        if m:
            day, mon, year = int(m.group(1)), m.group(2).lower()[:3], int(m.group(3))
            month = months.get(mon)
            if month:
                try:
                    pub = date(year, month, day)
                    data["days_on_market"] = (date.today() - pub).days
                except:
                    pass
    
    return data

def get_area_factor(address, lat, lon, station_coords):
    al = address.lower()
    for area, factor in AREA_FACTORS.items():
        if area in al:
            return factor
    # Distance-based
    dk = _haversine(lat, lon, *station_coords) / 1000
    if dk < 1: return 1.00
    elif dk < 2: return 0.95
    elif dk < 3: return 0.90
    elif dk < 5: return 0.85
    elif dk < 7: return 0.80
    else: return 0.75

def calculate_score(data, area_avg_m2):
    # Simple scoring logic
    score = 50  # Base
    
    # Age bonus
    age = data.get('age', 50)
    if age < 10: score += 15
    elif age < 30: score += 10
    elif age > 60: score -= 10
    
    # Price deal
    price_diff_pct = data.get('price_diff_pct', 0)
    if price_diff_pct < -10: score += 15
    elif price_diff_pct < -5: score += 10
    elif price_diff_pct > 15: score -= 15
    elif price_diff_pct > 5: score -= 10
    
    # Energy
    energy = data.get('energy', '')
    energy_scores = {'A': 15, 'B': 10, 'C': 5, 'D': 0, 'E': -5, 'F': -10, 'G': -15}
    score += energy_scores.get(energy, 0)
    
    # Distance
    dist = data.get('distance_to_station_m', 5000)
    if dist < 1000: score += 10
    elif dist < 2000: score += 5
    elif dist > 5000: score -= 10
    
    return max(0, min(100, score))

def analyze_property(finn_code, station="asker"):
    # Get FINN data
    finn_data = get_finn_data(finn_code)
    
    if not finn_data.get('address'):
        raise ValueError("Could not extract address from FINN listing")
    
    # Geocode
    geo = geocode(finn_data['address'])
    if not geo:
        raise ValueError(f"Could not geocode address: {finn_data['address']}")
    
    # Calculate metrics
    station_info = STATIONS.get(station, STATIONS['asker'])
    distance = _haversine(geo['lat'], geo['lon'], *station_info['coords'])
    
    area_factor = get_area_factor(finn_data['address'], geo['lat'], geo['lon'], station_info['coords'])
    
    # Mock area average (in real app, fetch from SSB)
    area_avg_m2 = 60000  # Placeholder
    area_avg_adjusted = area_avg_m2 * area_factor
    
    price_per_m2 = finn_data['price'] / finn_data['area'] if finn_data['area'] > 0 else 0
    price_diff_pct = ((area_avg_adjusted - price_per_m2) / area_avg_adjusted * 100) if area_avg_adjusted > 0 else 0
    
    age = date.today().year - finn_data['year'] if finn_data['year'] > 0 else None
    
    # Compile result
    result = {
        'finn_code': finn_code,
        'address': finn_data['address'],
        'price': finn_data['price'],
        'area': finn_data['area'],
        'price_per_m2': int(price_per_m2),
        'bedrooms': finn_data['bedrooms'],
        'rooms': finn_data['rooms'],
        'year': finn_data['year'],
        'age': age,
        'energy': finn_data['energy'],
        'tomt': finn_data['tomt'],
        'days_on_market': finn_data.get('days_on_market'),
        'distance_to_station_m': int(distance),
        'station': station,
        'lat': geo['lat'],
        'lon': geo['lon'],
        'area_avg_adjusted': int(area_avg_adjusted),
        'price_diff_pct': round(price_diff_pct, 1),
        'area_factor': area_factor,
    }
    
    # Calculate score
    result['score'] = calculate_score(result, area_avg_adjusted)
    
    # Score breakdown for radar
    result['score_breakdown'] = {
        'Byggeår': max(0, min(100, 100 - age * 1.3)) if age else 50,
        'Station Dist': max(0, min(100, 100 - distance/60)) if distance else 50,
        'Area Brai': max(0, min(100, finn_data['area'] - 50)),
        'Tomt': max(0, min(100, finn_data['tomt'] / 10)),
        'Bedrooms': finn_data['bedrooms'] * 25 if finn_data['bedrooms'] else 50,
        'Energy': {'A':100,'B':85,'C':65,'D':45,'E':25,'F':10,'G':0}.get(finn_data.get('energy',''),50),
        'Price Deal': max(0, min(100, 50 + price_diff_pct * 2)),
        'Family': 50,  # Placeholder
    }
    
    return result
