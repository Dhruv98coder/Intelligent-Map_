
import json, re, urllib.parse, urllib.request, urllib.error
from django.http import JsonResponse
from django.shortcuts import render
from .services.data_loader import load_all_metro_data
from .services.route_finder import MetroRouteFinder
from .services.station_search import StationSearch

OSRM = "https://router.project-osrm.org/route/v1/foot"


def _req(url):
    req=urllib.request.Request(url,headers={"User-Agent":"GoPlan-IntelligentMap/3.0"})
    with urllib.request.urlopen(req,timeout=25) as r:
        return json.loads(r.read().decode())


def _foot_route(a,b):
    coords=f"{a['longitude']},{a['latitude']};{b['longitude']},{b['latitude']}"
    url=f"{OSRM}/{coords}?"+urllib.parse.urlencode({"steps":"true","geometries":"geojson","overview":"full"})
    try:
        data=_req(url)
        route=(data.get("routes") or [None])[0]
        if not route: return None
        return {"geometry":route.get("geometry"),"distance_m":round(route.get("distance",0)),
                "duration_min":round(route.get("duration",0)/60)}
    except Exception:
        return None


def metro_map(request):
    try:
        from .services.graph_builder import MetroGraph
        graph=MetroGraph()
        stations=graph.all_stations()
        line_paths={k:[{"id":x["id"],"name":x["name"],"latitude":x["latitude"],"longitude":x["longitude"]} for x in v]
                    for k,v in graph.line_paths.items()}
        interchange_map={str(k):v for k,v in graph.interchange_details.items()}
        return render(request,"metro.html",{"stations":stations,"stations_json":json.dumps(stations),
                                            "line_paths_json":json.dumps(line_paths),
                                            "interchange_json":json.dumps(interchange_map)})
    except Exception as e:
        return render(request,"metro.html",{"stations":[],"stations_json":"[]","line_paths_json":"{}","interchange_json":"{}","error":str(e)})


def _station_query_variants(q):
    """Normalize common Delhi Metro spellings used by passengers."""
    q = re.sub(r"\s+", " ", str(q or "").strip())
    low = q.lower()
    aliases = {
        "sahid sthal": "Shaheed Sthal",
        "shahid sthal": "Shaheed Sthal",
        "sahid sthal": "Shaheed Sthal",
        "shaheed sthal": "Shaheed Sthal",
        "rajiv chowk": "Rajiv Chowk",
        "rajiv chawk": "Rajiv Chowk",
        "huda city centre": "Huda City Centre",
        "huda city center": "Huda City Centre",
    }
    return [aliases.get(low, q), q]


def station_search(request):
    q = request.GET.get("q", "").strip()
    if len(q) < 2:
        return JsonResponse({"results": []})
    try:
        search = StationSearch()
        combined = []
        seen = set()
        for variant in _station_query_variants(q):
            for s in search.search(variant, top_k=10):
                if s["id"] not in seen:
                    seen.add(s["id"])
                    combined.append(s)
        return JsonResponse({"results": combined[:10]})
    except Exception as e:
        return JsonResponse({"results": [], "error": str(e)})


def metro_route(request):
    start = request.GET.get("start", "").strip()
    dest = request.GET.get("destination", "").strip()
    if not start or not dest:
        return JsonResponse({"error": "Choose both stations."}, status=400)

    try:
        search = StationSearch()
        sres, dres = [], []
        for variant in _station_query_variants(start):
            sres += search.search(variant, top_k=10)
        for variant in _station_query_variants(dest):
            dres += search.search(variant, top_k=10)

        # Prefer exact normalized names, otherwise the best scored match.
        def pick(items, query):
            qn = re.sub(r"[^a-z0-9 ]", "", query.lower()).strip()
            for item in items:
                if re.sub(r"[^a-z0-9 ]", "", item["name"].lower()).strip() == qn:
                    return item
            return items[0] if items else None

        s, d = pick(sres, start), pick(dres, dest)
        if not s or not d:
            return JsonResponse({
                "success": False,
                "error": "Metro station not found. Try the station name, e.g. 'Shaheed Sthal' or 'Rajiv Chowk'."
            }, status=404)

        route = MetroRouteFinder().find_route(s["id"], d["id"])
        if not route:
            return JsonResponse({"success": False, "error": "No connected metro route found."}, status=404)

        instructions = []
        for leg in route["legs"]:
            instructions.append({
                "type": "board",
                "title": f"Board {leg['line']}",
                "text": f"At {leg['start_station']['name']}, board the {leg['line']} {leg['direction']}.",
                "stations": [x["name"] for x in leg["stations"]],
                "stops": leg["stops"],
            })
            if leg["stops"]:
                instructions.append({
                    "type": "ride",
                    "title": f"Stay on {leg['line']} for {leg['stops']} stop(s)",
                    "text": "Pass: " + " → ".join(x["name"] for x in leg["stations"][1:]),
                    "stations": [x["name"] for x in leg["stations"]],
                    "stops": leg["stops"],
                })

        for change in route["interchanges"]:
            instructions.append({
                "type": "interchange",
                "title": f"Interchange at {change['station_name']}",
                "text": f"Change from {change['from_line']} to {change['to_line']}. "
                         f"Estimated indoor transfer: {change.get('estimated_walk_m',250)} m / "
                         f"{change.get('estimated_walk_min',4)} min.",
                "from_line": change["from_line"],
                "to_line": change["to_line"],
                "station_name": change["station_name"],
                "walk_m": change.get("estimated_walk_m",250),
                "walk_min": change.get("estimated_walk_min",4),
                "steps": change.get("steps",[]),
            })

        instructions.append({
            "type": "exit",
            "title": f"Exit at {route['stations'][-1]['name']}",
            "text": f"Get off at {route['stations'][-1]['name']} and follow the exit signs for your final road destination.",
        })

        return JsonResponse({
            "success": True,
            "from": s,
            "to": d,
            "route": route,
            "instructions": instructions,
            "note": "Metro time is an estimate, not a live train timetable. Platform/exit availability can change."
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)

def metro_walk_route(request):
    try:
        a={"latitude":float(request.GET["from_lat"]),"longitude":float(request.GET["from_lon"])}
        b={"latitude":float(request.GET["to_lat"]),"longitude":float(request.GET["to_lon"])}
        return JsonResponse({"success":True,"route":_foot_route(a,b)})
    except Exception as e:
        return JsonResponse({"success":False,"error":str(e)},status=400)
