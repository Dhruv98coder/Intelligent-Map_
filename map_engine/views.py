
import csv
import re
import json
import math
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie

OSRM_URL = "https://router.project-osrm.org/route/v1"
BIKE_ROUTER_URL = os.environ.get("GOPLAN_BIKE_ROUTER_URL", "https://routing.openstreetmap.de/routed-bike/route/v1/driving")
FOOT_ROUTER_URL = os.environ.get("GOPLAN_FOOT_ROUTER_URL", "https://routing.openstreetmap.de/routed-foot/route/v1/driving")
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_PATH = os.path.join(os.path.dirname(BASE_DIR), "dataset", "GoPlan_Delhi_Places_AI_Dataset_READABLE(final).csv")

# Delhi NCR safety fence: Delhi + Gurugram + Noida/Greater Noida + Ghaziabad + Faridabad.
# Operational NCR envelope. It deliberately covers the full NCR search/routing
# area (including Bulandshahr and the wider Haryana/UP/Rajasthan NCR districts)
# instead of the old Delhi-core-only rectangle.
# (south, west, north, east)
NCR_BBOX = (27.05, 75.85, 29.85, 78.70)
USER_AGENT = os.environ.get(
    "GOPLAN_USER_AGENT",
    "GoPlan-IntelligentMap/6.0 (NCR place search; contact admin)"
)

# Instantly searchable Delhi NCR cities/localities (no keystroke-by-keystroke
# Nominatim calls needed for these). Keeps every part of NCR — Delhi, New Delhi,
# Ghaziabad, Noida, Gurugram, Faridabad and their well-known localities —
# reachable the moment the user starts typing.
NCR_LOCALITIES = [
    {"name": "New Delhi", "aliases": ["newdelhi"], "latitude": 28.6139, "longitude": 77.2090, "category": "City"},
    {"name": "Old Delhi", "aliases": ["puranidilli"], "latitude": 28.6562, "longitude": 77.2410, "category": "City area"},
    {"name": "Delhi", "aliases": ["dilli"], "latitude": 28.7041, "longitude": 77.1025, "category": "City"},
    {"name": "Dwarka", "aliases": ["dwaraka"], "latitude": 28.5921, "longitude": 77.0460, "category": "Sub-city, Delhi"},
    {"name": "Rohini", "aliases": [], "latitude": 28.7495, "longitude": 77.0565, "category": "Sub-city, Delhi"},
    {"name": "Saket", "aliases": [], "latitude": 28.5245, "longitude": 77.2066, "category": "Locality, South Delhi"},
    {"name": "Vasant Kunj", "aliases": [], "latitude": 28.5200, "longitude": 77.1590, "category": "Locality, South Delhi"},
    {"name": "Karol Bagh", "aliases": ["karolbagh"], "latitude": 28.6519, "longitude": 77.1909, "category": "Locality, Central Delhi"},
    {"name": "Pitampura", "aliases": [], "latitude": 28.6980, "longitude": 77.1315, "category": "Locality, North West Delhi"},
    {"name": "Ghaziabad", "aliases": ["gaziabad", "gaziyabad", "ghaziabd", "ghaziyabad"], "latitude": 28.6692, "longitude": 77.4538, "category": "City, NCR (UP)"},
    {"name": "Duhai", "aliases": ["duhaii", "dohai"], "latitude": 28.7717, "longitude": 77.5230, "category": "Town, Ghaziabad NCR"},
    {"name": "Vaishali", "aliases": [], "latitude": 28.6469, "longitude": 77.3389, "category": "Locality, Ghaziabad NCR"},
    {"name": "Indirapuram", "aliases": ["indrapuram"], "latitude": 28.6461, "longitude": 77.3720, "category": "Locality, Ghaziabad NCR"},
    {"name": "Vasundhara", "aliases": [], "latitude": 28.6603, "longitude": 77.3576, "category": "Locality, Ghaziabad NCR"},
    {"name": "Noida", "aliases": ["naeda"], "latitude": 28.5355, "longitude": 77.3910, "category": "City, NCR (UP)"},
    {"name": "Greater Noida", "aliases": ["greaternoida"], "latitude": 28.4744, "longitude": 77.5040, "category": "City, NCR (UP)"},
    {"name": "Gurugram", "aliases": ["gurgaon", "gurgoan", "gurgao"], "latitude": 28.4595, "longitude": 77.0266, "category": "City, NCR (Haryana)"},
    {"name": "Faridabad", "aliases": ["faridbad"], "latitude": 28.4089, "longitude": 77.3178, "category": "City, NCR (Haryana)"},
]


# NCR district / major-town index gives instant results for the wider region,
# while remote OSM search handles the long tail of roads, businesses and landmarks.
NCR_MAJOR_PLACES = [
    ("Meerut", 28.9845, 77.7064, "City, Uttar Pradesh NCR"),
    ("Hapur", 28.7306, 77.7759, "City, Uttar Pradesh NCR"),
    ("Baghpat", 28.9440, 77.2189, "City, Uttar Pradesh NCR"),
    ("Muzaffarnagar", 29.4727, 77.7085, "City, Uttar Pradesh NCR"),
    ("Shamli", 29.4497, 77.3095, "City, Uttar Pradesh NCR"),
    ("Sikandrabad", 28.4524, 77.6992, "Town, Bulandshahr NCR"),
    ("Khurja", 28.2526, 77.8513, "City, Bulandshahr NCR"),
    ("Siyana", 28.6135, 78.0538, "Town, Bulandshahr NCR"),
    ("Anupshahr", 28.3578, 78.2691, "Town, Bulandshahr NCR"),
    ("Gurugram", 28.4595, 77.0266, "City, Haryana NCR"),
    ("Manesar", 28.3515, 76.9428, "Town, Haryana NCR"),
    ("Sonipat", 28.9931, 77.0151, "City, Haryana NCR"),
    ("Panipat", 29.3909, 76.9635, "City, Haryana NCR"),
    ("Rohtak", 28.8955, 76.6066, "City, Haryana NCR"),
    ("Jhajjar", 28.6068, 76.6560, "City, Haryana NCR"),
    ("Rewari", 28.1990, 76.6183, "City, Haryana NCR"),
    ("Palwal", 28.1487, 77.3320, "City, Haryana NCR"),
    ("Nuh", 28.1027, 77.0194, "City, Haryana NCR"),
    ("Bhiwani", 28.7930, 76.1396, "City, Haryana NCR"),
    ("Karnal", 29.6857, 76.9905, "City, Haryana NCR"),
    ("Jind", 29.3158, 76.3150, "City, Haryana NCR"),
    ("Mahendragarh", 28.2732, 76.1445, "Town, Haryana NCR"),
    ("Alwar", 27.5530, 76.6346, "City, Rajasthan NCR"),
    ("Bharatpur", 27.2152, 77.4900, "City, Rajasthan NCR"),
]

for _name, _lat, _lon, _category in NCR_MAJOR_PLACES:
    NCR_LOCALITIES.append({"name": _name, "aliases": [], "latitude": _lat, "longitude": _lon, "category": _category})


def _json_request(url, method="GET", data=None, headers=None, timeout=25):
    headers = headers or {}
    body = None
    if data is not None:
        if headers.get("Content-Type", "").startswith("application/x-www-form-urlencoded"):
            body = urllib.parse.urlencode(data).encode()
        else:
            body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _in_ncr(lat, lon):
    return NCR_BBOX[0] <= lat <= NCR_BBOX[2] and NCR_BBOX[1] <= lon <= NCR_BBOX[3]


def _distance_km(lat1, lon1, lat2, lon2):
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def _load_dataset_places():
    places = []
    if not os.path.exists(DATASET_PATH):
        return places
    try:
        with open(DATASET_PATH, "r", encoding="utf-8-sig", newline="") as f:
            sample = f.read(4096)
            f.seek(0)
            dialect = csv.Sniffer().sniff(sample, delimiters="\t,;")
            reader = csv.DictReader(f, dialect=dialect)
            for row in reader:
                try:
                    lat = float(row.get("latitude") or row.get("destination_latitude"))
                    lon = float(row.get("longitude") or row.get("destination_longitude"))
                except (TypeError, ValueError):
                    continue
                if not _in_ncr(lat, lon):
                    continue
                places.append({
                    "name": row.get("place_name") or row.get("name") or "Place",
                    "category": row.get("category") or row.get("broad_category") or "Tourist place",
                    "latitude": lat, "longitude": lon,
                    "description": row.get("description", ""),
                    "rating": row.get("rating", ""),
                    "best_time": row.get("best_time_suggestion") or row.get("best_time_season", ""),
                    "awareness_tips": row.get("awareness_tips", ""),
                    "entry_fee": row.get("entry_fee_foreigner") or row.get("entry_fee_indian", ""),
                    "source": "GoPlan dataset"
                })
    except Exception:
        pass
    return places


@ensure_csrf_cookie
def map_home(request):
    return render(request, "map_engine/map.html")


def _format_duration(seconds):
    minutes = max(0, round(float(seconds or 0)/60))
    return f"{minutes//60} hr {minutes%60:02d} min" if minutes >= 60 else f"{minutes} min"


def _route(profile, start, end):
    coords = f"{start['longitude']},{start['latitude']};{end['longitude']},{end['latitude']}"
    if profile == "bike":
        base = BIKE_ROUTER_URL
    elif profile == "foot":
        base = FOOT_ROUTER_URL
    else:
        base = f"{OSRM_URL}/driving"
    query = urllib.parse.urlencode({
        "alternatives": "2", "steps": "true", "geometries": "geojson",
        "overview": "full", "annotations": "true"
    })
    url = f"{base}/{coords}?{query}"
    return _json_request(url, headers={"User-Agent": USER_AGENT}, timeout=30)


def _clean_osrm_route(route, idx):
    steps = []
    for leg in route.get("legs", []):
        for s in leg.get("steps", []):
            maneuver = s.get("maneuver", {})
            steps.append({
                "instruction": s.get("name") or "Continue",
                "type": maneuver.get("type", ""),
                "modifier": maneuver.get("modifier", ""),
                "distance_m": round(s.get("distance", 0)),
                "duration_min": round(s.get("duration", 0)/60),
                "location": [maneuver.get("location", [0,0])[1], maneuver.get("location", [0,0])[0]]
            })
    return {
        "index": idx,
        "geometry": route.get("geometry"),
        "distance_km": round(route.get("distance", 0)/1000, 2),
        "distance_text": f"{route.get('distance',0)/1000:.1f} km",
        "duration_minutes": round(route.get("duration", 0)/60),
        "duration_text": _format_duration(route.get("duration", 0)),
        "steps": steps[:80]
    }


def calculate_route(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST required"}, status=405)
    try:
        payload = json.loads(request.body)
        start, dest = payload["from"], payload["to"]
        mode = str(payload.get("mode", "car")).lower()
        start = {"latitude": float(start["latitude"]), "longitude": float(start["longitude"])}
        dest = {"latitude": float(dest["latitude"]), "longitude": float(dest["longitude"])}
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({"success": False, "error": "Invalid start or destination"}, status=400)
    profiles = {"car": "car", "bike": "bike", "foot": "foot"}
    if mode not in profiles:
        return JsonResponse({"success": False, "error": "Use the Metro planner for metro and the Rail planner for trains."}, status=400)
    if not (_in_ncr(start["latitude"], start["longitude"]) and _in_ncr(dest["latitude"], dest["longitude"])):
        return JsonResponse({"success": False, "error": "GoPlan road navigation covers Delhi NCR only (Delhi, New Delhi, Ghaziabad, Noida, Greater Noida, Gurugram, Faridabad)."}, status=400)
    try:
        data = _route(profiles[mode], start, dest)
    except Exception as e:
        return JsonResponse({"success": False, "error": f"Road routing unavailable: {e}"}, status=502)
    routes = [_clean_osrm_route(r, i) for i, r in enumerate(data.get("routes", [])[:3])]
    if not routes:
        return JsonResponse({"success": False, "error": "No road route found."}, status=404)
    return JsonResponse({"success": True, "mode": mode, "routes": routes, "route": routes[0]})


def _nominatim_results(query, bounded=False, limit=20):
    """Search real-world places through Nominatim.

    GoPlan IntelligentMap is a Delhi NCR map: remote lookups are bounded
    (``bounded=1`` + NCR viewbox) so results stay inside Delhi, New Delhi,
    Ghaziabad, Noida, Greater Noida, Gurugram and Faridabad.
    """
    params = {
        "q": query,
        "format": "jsonv2",
        "limit": limit,
        "addressdetails": 1,
        "namedetails": 1,
        "countrycodes": "in",
        "accept-language": "en",
    }
    # Viewbox is only a ranking hint when bounded=False. Do NOT hard-limit the
    # geocoder to the rectangle: that was the reason valid mapped places were
    # being missed. We filter the returned candidates against NCR afterwards.
    params["viewbox"] = f"{NCR_BBOX[1]},{NCR_BBOX[2]},{NCR_BBOX[3]},{NCR_BBOX[0]}"
    if bounded:
        params["bounded"] = 1
    return _json_request(
        f"{NOMINATIM_URL}?{urllib.parse.urlencode(params)}",
        headers={"User-Agent": USER_AGENT},
        timeout=18,
    )


def _place_search_score(item, query):
    """Rank local/OSM results without requiring a third-party geocoding package."""
    from difflib import SequenceMatcher

    q = re.sub(r"\s+", " ", str(query or "").strip().lower())
    if not q:
        return 0.0

    name = str(item.get("name") or "").strip().lower()
    display = str(item.get("display_name") or "").lower()
    address = item.get("address") or {}
    aliases = " ".join(str(v) for v in item.get("aliases", [])).lower()
    hay = " ".join([name, display, aliases])

    score = 0.0
    if name == q:
        score += 5000
    elif name.startswith(q):
        score += 4000
    elif q in name:
        score += 3200
    elif q in hay:
        score += 2200

    # Token match helps with searches such as "red fort delhi".
    q_tokens = [t for t in re.findall(r"[a-z0-9]+", q) if len(t) > 1]
    if q_tokens:
        matched = sum(t in hay for t in q_tokens)
        score += 500 * (matched / len(q_tokens))

    # Fuzzy matching covers small spelling mistakes like "bulandsher".
    compact_q = re.sub(r"[^a-z0-9]", "", q)
    compact_name = re.sub(r"[^a-z0-9]", "", name)
    if compact_q and compact_name:
        ratio = SequenceMatcher(None, compact_q, compact_name).ratio()
        if ratio >= 0.70:
            score += ratio * 1800

    # Prefer actual populated places/businesses over boundary metadata.
    item_type = str(item.get("type") or "").lower()
    if item_type in {"city", "town", "village", "suburb", "neighbourhood", "locality", "place"}:
        score += 120
    if any(k in address for k in ("city", "town", "municipality", "suburb")):
        score += 60
    return score


def _normalise_query(q):
    """Normalise common NCR/Indian place spellings before remote search."""
    value = re.sub(r"\s+", " ", q.strip())
    replacements = {
        "bulandsher": "Bulandshahr",
        "bulandshar": "Bulandshahr",
        "bulandshahar": "Bulandshahr",
        "bulandshair": "Bulandshahr",
        "bulandshr": "Bulandshahr",
        "ghaziabad": "Ghaziabad",
        "gaziabad": "Ghaziabad",
        "gaziyabad": "Ghaziabad",
        "ghaziyabad": "Ghaziabad",
        "ghaziabd": "Ghaziabad",
        "gurgoan": "Gurugram",
        "gurgaon": "Gurugram",
        "gurgao": "Gurugram",
        "faridbad": "Faridabad",
        "greaternoida": "Greater Noida",
        "greter noida": "Greater Noida",
    }
    low = value.lower()
    return replacements.get(low, value)


def _search_query_variants(q):
    """Generate useful variants while keeping the original query first."""
    clean = re.sub(r"\s+", " ", q.strip())
    normal = _normalise_query(clean)
    variants = [clean]
    if normal.lower() != clean.lower():
        variants.append(normal)

    low = normal.lower()
    # NCR is intentionally broader than the Delhi core. Explicit hints help
    # Nominatim resolve small towns/landmarks with common names.
    if not any(x in low for x in (
        "delhi", "noida", "gurugram", "gurgaon", "ghaziabad", "faridabad",
        "meerut", "bulandshahr", "bulandshahar", "baghpat", "hapur", "muzaffarnagar",
        "shamli", "sonipat", "panipat", "rohtak", "jhajjar", "rewari", "palwal",
        "alwar", "bharatpur", "karnal", "jind", "bhiwani", "mahendragarh", "nuh"
    )):
        variants.extend([
            f"{normal}, Delhi NCR",
            f"{normal}, Uttar Pradesh",
            f"{normal}, Haryana",
            f"{normal}, Rajasthan",
            f"{normal}, Delhi",
        ])
    # Common transliteration / spacing variants. These are kept conservative
    # so a normal place query still resolves directly on the original text.
    compact = re.sub(r"[^a-z0-9]", "", low)
    if compact and compact != low.replace(" ", ""):
        variants.append(compact)
    return list(dict.fromkeys(variants))


def _normalise_search_result(item):
    try:
        lat, lon = float(item["lat"]), float(item["lon"])
    except (KeyError, TypeError, ValueError):
        return None
    display = item.get("display_name", "Unknown place")
    names = item.get("namedetails", {}) or {}
    address = item.get("address", {}) or {}
    name = names.get("name") or display.split(",")[0].strip() or "Place"
    locality = ", ".join(str(address.get(k, "")) for k in ("suburb", "city_district", "city", "town", "municipality", "state_district", "state") if address.get(k))
    return {
        "name": name,
        "display_name": display,
        "latitude": lat,
        "longitude": lon,
        "type": item.get("type", ""),
        "category": item.get("category", "place"),
        "locality": locality,
        "source": "OpenStreetMap / Nominatim",
        "_score": _place_search_score({"name": name, "display_name": display, "address": address}, name),
    }


def _overpass_name_search(query, limit=80):
    """Search the OpenStreetMap object index directly by name/alt_name."""
    clean = re.sub(r"\s+", " ", str(query or "").strip())
    if len(clean) < 2:
        return []
    pattern = re.escape(clean[:80])
    south, west, north, east = NCR_BBOX
    ql = ('[out:json][timeout:20];'
          '(nwr["name"~"%s",i](%s,%s,%s,%s);'
          'nwr["alt_name"~"%s",i](%s,%s,%s,%s););'
          'out center tags;' % (pattern, south, west, north, east,
                                pattern, south, west, north, east))
    try:
        data = _json_request(
            OVERPASS_URL,
            method="POST",
            data=ql,
            headers={"Content-Type": "text/plain", "User-Agent": USER_AGENT},
            timeout=25,
        )
    except Exception:
        return []
    out = []
    elements = data.get("elements", []) if isinstance(data, dict) else []
    for element in elements:
        tags = element.get("tags", {}) or {}
        name = tags.get("name") or tags.get("alt_name") or tags.get("name:en")
        center = element.get("center") or {}
        lat = element.get("lat", center.get("lat"))
        lon = element.get("lon", center.get("lon"))
        try:
            lat, lon = float(lat), float(lon)
        except (TypeError, ValueError):
            continue
        if not _in_ncr(lat, lon) or not name:
            continue
        display = ", ".join(x for x in [name, tags.get("addr:city"), tags.get("addr:district"), tags.get("addr:state")] if x)
        out.append({
            "name": name,
            "display_name": display,
            "latitude": lat,
            "longitude": lon,
            "type": element.get("type", ""),
            "category": tags.get("amenity") or tags.get("highway") or tags.get("tourism") or tags.get("railway") or tags.get("place") or "mapped place",
            "source": "OpenStreetMap / Overpass",
            "_score": _place_search_score({"name": name, "display_name": display, "type": tags.get("place") or element.get("type", "")}, clean) + 700,
        })
    return out[:limit]


def search_places(request):
    q = re.sub(r"\s+", " ", request.GET.get("q", "").strip())
    if len(q) < 2:
        return JsonResponse({"results": [], "query": q})

    results = []
    # Curated dataset + metro index + NCR locality index stay useful as fast,
    # instant (no remote call needed) local sources.
    try:
        from metro.services.station_search import StationSearch
        for p in StationSearch().search(q, top_k=8):
            results.append({
                "name": p["name"], "display_name": f"{p['name']} • Delhi NCR Metro",
                "latitude": p["latitude"], "longitude": p["longitude"],
                "category": "Metro station", "source": "DMRC 2026 dataset", "_score": 9000
            })
    except Exception:
        pass

    qlow = _normalise_query(q).lower().strip()
    for loc in NCR_LOCALITIES:
        names = [loc["name"].lower()] + loc.get("aliases", [])
        if any(qlow in n or n.startswith(qlow) for n in names):
            results.append({
                "name": loc["name"], "display_name": f"{loc['name']} • Delhi NCR",
                "latitude": loc["latitude"], "longitude": loc["longitude"],
                "category": loc["category"], "source": "GoPlan NCR locality index", "_score": 8500
            })

    tokens = [t for t in re.findall(r"[a-z0-9]+", q.lower()) if len(t) > 1]
    for p in _load_dataset_places():
        hay = f"{p['name']} {p['category']} {p['description']}".lower()
        if q.lower() in hay or (tokens and sum(t in hay for t in tokens) >= max(1, len(tokens)-1)):
            results.append({**p, "display_name": f"{p['name']} • GoPlan dataset", "source": "GoPlan dataset", "_score": 8000})

    # Explicit submit/Enter performs the live place search. The map remains
    # NCR-only, but the geocoder itself is not artificially clipped; candidates
    # are filtered by our NCR bbox after retrieval.
    if request.GET.get("remote") == "1":
        seen_osm = set()
        for query in _search_query_variants(q):
            try:
                # IMPORTANT: don't use bounded=1 here. Nominatim's bounded search
                # can omit legitimate OSM places near/inside NCR when the query
                # itself is broad (roads, villages, markets, institutions, etc.).
                # We fetch candidates with NCR as the viewbox preference and then
                # apply our own exact NCR geographic filter below.
                data = _nominatim_results(query, bounded=False, limit=20)
            except Exception:
                continue
            for item in data if isinstance(data, list) else []:
                r = _normalise_search_result(item)
                if not r or not _in_ncr(r["latitude"], r["longitude"]):
                    continue
                key = (item.get("osm_type"), item.get("osm_id"))
                if key == (None, None):
                    key = (round(r["latitude"], 5), round(r["longitude"], 5))
                if key in seen_osm:
                    continue
                seen_osm.add(key)
                r["_score"] = _place_search_score({
                    "name": r["name"],
                    "display_name": r["display_name"],
                    "address": item.get("address", {}),
                    "type": item.get("type", "")
                }, q)
                # Exact coordinate hits and strong textual matches should win.
                r["_score"] += 250 if r["name"].strip().lower() == _normalise_query(q).strip().lower() else 0
                results.append(r)
            if len(results) >= 80:
                break

        # Direct OSM name-index fallback catches named map objects that a
        # geocoder may rank too low: roads, villages, markets, institutions,
        # stations, parks and other mapped objects.
        for query in _search_query_variants(q)[:3]:
            for r in _overpass_name_search(query, limit=80):
                key = (round(float(r["latitude"]), 5), round(float(r["longitude"]), 5))
                if not any((round(float(x.get("latitude", 999)), 5), round(float(x.get("longitude", 999)), 5)) == key for x in results):
                    results.append(r)
            if len(results) >= 100:
                break

    out, seen = [], set()
    for r in sorted(results, key=lambda x: -float(x.get("_score", 0))):
        try:
            key = (round(float(r["latitude"]), 5), round(float(r["longitude"]), 5))
        except (KeyError, TypeError, ValueError):
            continue
        if key in seen:
            continue
        seen.add(key)
        r.pop("_score", None)
        out.append(r)

    return JsonResponse({
        "results": out[:30],
        "query": q,
        "scope": "Delhi NCR",
        "search_note": (
            "Delhi NCR wide search: Delhi, Haryana NCR, Uttar Pradesh NCR, "
            "Rajasthan NCR, towns, landmarks, roads, businesses and mapped places."
        )
    })


NEARBY = {
    "metro": 'nwr["railway"="station"]["station"="subway"](around:{r},{lat},{lon});',
    "train": 'nwr["railway"="station"]["station"!="subway"](around:{r},{lat},{lon});',
    "food": 'nwr["amenity"~"restaurant|cafe|fast_food|food_court"](around:{r},{lat},{lon});',
    "hotel": 'nwr["tourism"~"hotel|hostel|guest_house"](around:{r},{lat},{lon});',
    "hospital": 'nwr["amenity"="hospital"](around:{r},{lat},{lon});',
    "atm": 'nwr["amenity"="atm"](around:{r},{lat},{lon});',
    "tourist": 'nwr["tourism"~"attraction|museum|gallery|viewpoint|zoo|theme_park|information"](around:{r},{lat},{lon});nwr["historic"](around:{r},{lat},{lon});nwr["leisure"="park"](around:{r},{lat},{lon});',

    "pharmacy": 'nwr["amenity"="pharmacy"](around:{r},{lat},{lon});'
}


def _nearest_bus_stop(lat, lon, radius=1800):
    """Return the nearest mapped OSM bus stop near a coordinate."""
    query = f'''[out:json][timeout:15];
    (nwr["highway"="bus_stop"](around:{int(radius)},{lat},{lon});
     nwr["public_transport"="platform"]["bus"="yes"](around:{int(radius)},{lat},{lon}););
    out center tags;'''
    try:
        data = _json_request(OVERPASS_URL, method="POST", data=query,
                              headers={"Content-Type":"text/plain", "User-Agent":USER_AGENT}, timeout=20)
    except Exception:
        return None
    best=None
    for el in data.get("elements", []):
        tags=el.get("tags",{}) or {}
        name=tags.get("name") or tags.get("name:en") or "Bus stop"
        c=el.get("center",{}) or {}
        e_lat=el.get("lat",c.get("lat")); e_lon=el.get("lon",c.get("lon"))
        try:e_lat,e_lon=float(e_lat),float(e_lon)
        except (TypeError,ValueError):continue
        d=_distance_km(lat,lon,e_lat,e_lon)*1000
        if best is None or d<best["distance_m"]:
            best={"name":name,"latitude":e_lat,"longitude":e_lon,"distance_m":round(d)}
    return best


def smart_connect(request):
    """Build a clearly-labelled auto + bus + walk suggestion.

    OSM gives nearby bus stops, but it does not provide a reliable live Delhi
    bus timetable/fare graph. Therefore this endpoint returns an estimated bus
    leg instead of pretending to know a live bus departure.
    """
    try:
        flat,flon=float(request.GET["from_lat"]),float(request.GET["from_lon"])
        tlat,tlon=float(request.GET["to_lat"]),float(request.GET["to_lon"])
        road_km=max(0.5,float(request.GET.get("distance_km", "1")))
    except (KeyError,ValueError):
        return JsonResponse({"success":False,"error":"Invalid coordinates"},status=400)
    if not (_in_ncr(flat,flon) and _in_ncr(tlat,tlon)):
        return JsonResponse({"success":False,"error":"Delhi NCR only"},status=400)

    origin_stop=_nearest_bus_stop(flat,flon)
    destination_stop=_nearest_bus_stop(tlat,tlon)
    if not origin_stop and not destination_stop:
        return JsonResponse({"success":False,"error":"No mapped bus stops found nearby"},status=404)

    pickup_km=(origin_stop["distance_m"]/1000) if origin_stop else 0.6
    final_km=(destination_stop["distance_m"]/1000) if destination_stop else 0.5
    # Conservative UI estimates, never presented as official/live fares.
    auto_fare=max(30,round((30+12*pickup_km)/5)*5)
    bus_distance=max(1.0,road_km-pickup_km-final_km)
    bus_fare=min(40,max(10,round((10+1.4*bus_distance)/5)*5))
    walk_min=round(final_km*12)
    auto_min=max(3,round(pickup_km*5))
    bus_min=max(8,round(bus_distance/18*60))
    total_fare=auto_fare+bus_fare
    total_min=auto_min+bus_min+walk_min
    return JsonResponse({
        "success":True,"origin_stop":origin_stop or {},"destination_stop":destination_stop or {},
        "auto_fare":auto_fare,"bus_fare":bus_fare,"total_fare":total_fare,
        "bus_text":f"~{bus_distance:.1f} km estimated bus leg · {bus_min} min planning estimate",
        "total_time_text":f"~{total_min} min",
        "note":"Bus route and fare are estimates from mapped stops; live bus/GTFS data is not being claimed."
    })


def nearby_places(request):
    try:
        lat, lon = float(request.GET["lat"]), float(request.GET["lon"])
        category = request.GET.get("type", "tourist").lower()
        radius = min(max(int(request.GET.get("radius", "12000")), 500), 25000)
    except (KeyError, ValueError):
        return JsonResponse({"results": [], "error": "Invalid coordinates"}, status=400)
    if not _in_ncr(lat, lon):
        return JsonResponse({"results": [], "error": "Delhi NCR only"}, status=400)
    results, seen = [], set()
    if category == "tourist":
        for p in _load_dataset_places():
            d = _distance_km(lat, lon, p["latitude"], p["longitude"])*1000
            if d <= radius:
                key=(round(p["latitude"],5),round(p["longitude"],5))
                seen.add(key); results.append({**p, "distance_m": round(d)})
    q = NEARBY.get(category)
    if q:
        try:
            query = f"[out:json][timeout:20];({q.format(r=radius,lat=lat,lon=lon)});out center tags;"
            data = _json_request(OVERPASS_URL, "POST", {"data": query},
                                 {"Content-Type":"application/x-www-form-urlencoded","User-Agent":"GoPlan-IntelligentMap/3.0"}, 25)
            for el in data.get("elements", []):
                tags=el.get("tags",{}); name=tags.get("name")
                e_lat=el.get("lat",el.get("center",{}).get("lat")); e_lon=el.get("lon",el.get("center",{}).get("lon"))
                if not name or e_lat is None or e_lon is None: continue
                e_lat,e_lon=float(e_lat),float(e_lon)
                key=(round(e_lat,5),round(e_lon,5))
                if key in seen: continue
                seen.add(key)
                results.append({"name":name,"category":category.title(),"latitude":e_lat,"longitude":e_lon,
                                "distance_m":round(_distance_km(lat,lon,e_lat,e_lon)*1000),
                                "description":tags.get("description",""),"source":"OpenStreetMap"})
        except Exception:
            pass
    results.sort(key=lambda x:x.get("distance_m",10**9))
    return JsonResponse({"results": results[:40], "category": category, "radius_m": radius, "scope": "Delhi NCR"})


def weather(request):
    try:
        lat, lon = float(request.GET["lat"]), float(request.GET["lon"])
    except (KeyError, ValueError):
        return JsonResponse({"error":"Invalid coordinates"}, status=400)
    params=urllib.parse.urlencode({
        "latitude":lat,"longitude":lon,
        "current":"temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,visibility",
        "daily":"weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max,sunrise,sunset",
        "forecast_days":7,"timezone":"auto"
    })
    try:
        data=_json_request(f"{WEATHER_URL}?{params}",headers={"User-Agent":USER_AGENT})
        data["goplan"] = {"scope": "Delhi NCR", "updated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z"}
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({"error":str(e)},status=502)


def awareness(request):
    # Context-aware, practical travel reminders; never presented as emergency advice.
    tips=[]
    hour=datetime.now().hour
    mode=request.GET.get("mode","car")
    if hour >= 22 or hour < 6:
        tips.append("Late-hour awareness: prefer well-lit, busy routes and keep your phone charged.")
    else:
        tips.append("Stay aware at crossings and keep your route visible while moving.")
    if mode == "foot": tips.append("Walking tip: use pedestrian crossings and sidewalks where available.")
    elif mode == "bike": tips.append("Bike tip: use a helmet, lights after dark, and stay alert around intersections.")
    elif mode == "car": tips.append("Driving tip: follow local signs and never interact with the phone while moving.")
    if request.GET.get("rain") == "1":
        tips.append("Rain-aware: allow extra travel time and watch for slippery surfaces.")
    return JsonResponse({"tips":tips})


def train_schedule(request):
    # Clearly labelled planning slots rather than pretending these are live railway departures.
    return JsonResponse({
        "title":"Rail planning",
        "notice":"These are planning windows, not live train departures.",
        "slots":[
            {"label":"Morning","time":"06:00–10:00","note":"Good for early departures"},
            {"label":"Day","time":"10:00–16:00","note":"Typical daytime planning window"},
            {"label":"Evening","time":"16:00–21:00","note":"Allow extra interchange time"},
            {"label":"Late","time":"21:00–23:00","note":"Check the operator before travelling"}
        ]
    })
