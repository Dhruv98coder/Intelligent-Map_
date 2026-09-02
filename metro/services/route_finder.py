
import heapq, math, re
from .graph_builder import MetroGraph, norm_name

class MetroRouteFinder:
    def __init__(self):
        self.metro=MetroGraph()

    def _fare(self, distance_km):
        # Fare CSV uses distance slabs. Keep a conservative fallback.
        rows=self.metro.fares
        if rows is None or rows.empty: return None
        normal=rows
        for _,r in normal.iterrows():
            slab=str(r.get("distance_slab",""))
            m=re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)",slab)
            if m and float(m.group(1))<=distance_km<=float(m.group(2)):
                return int(float(r.get("fare_inr",0)))
            if ">" in slab:
                m=re.search(r"(\d+(?:\.\d+)?)",slab)
                if m and distance_km>float(m.group(1)): return int(float(r.get("fare_inr",0)))
        return None

    def find_route(self,start_station_id,end_station_id):
        start=int(start_station_id); end=int(end_station_id)
        starts=[n for n in self.metro.graph if n[0]==start]
        goals={n for n in self.metro.graph if n[0]==end}
        if not starts or not goals: return None

        # Cost is minutes: riding roughly 2.5 min/km plus a 4-min transfer.
        # A tiny transfer tie-breaker avoids pointless changes.
        pq=[]; dist={}; prev={}
        for s in starts:
            dist[s]=0.0; heapq.heappush(pq,(0.0,0,s[1],s))
        goal=None
        while pq:
            cost,transfers,line,u=heapq.heappop(pq)
            if cost!=dist.get(u): continue
            if u in goals: goal=u; break
            for e in self.metro.graph.get(u,[]):
                v=e["to"]
                ride_min=2.2 if e["type"]=="ride" else 0
                transfer_min=4.0 if e["type"]=="transfer" else 0
                nc=cost+ride_min+transfer_min
                if nc<dist.get(v,1e99):
                    dist[v]=nc
                    prev[v]=(u,e)
                    heapq.heappush(pq,(nc,transfers+(e["type"]=="transfer"),v[1],v))
        if goal is None: return None

        nodes=[]; edges=[]
        u=goal
        while u in prev:
            nodes.append(u); pu,e=prev[u]; edges.append(e); u=pu
        nodes.append(u); nodes.reverse(); edges.reverse()

        # Compress duplicate transfer node pairs into station sequence.
        stations=[]
        for sid,line in nodes:
            s=self.metro.get_station(sid)
            stations.append({"id":sid,"name":re.sub(r"\s*\[Conn:.*?\]","",s["name"]).strip(),
                             "line":line,"latitude":s["latitude"],"longitude":s["longitude"]})
        legs=[]
        start_idx=0
        for i in range(1,len(stations)):
            if stations[i]["line"]!=stations[i-1]["line"]:
                legs.append(self._leg(stations[start_idx:i],len(legs)+1))
                start_idx=i
        legs.append(self._leg(stations[start_idx:],len(legs)+1))
        interchanges=[]
        for i,e in enumerate(edges):
            if e["type"]=="transfer":
                detail=e.get("detail") or {}
                interchanges.append({
                    **detail,"step_index":i+1
                })

        distance=sum(e.get("distance_km",0) for e in edges if e["type"]=="ride")
        minutes=round(sum(2.2 + (4 if e["type"]=="transfer" else 0) for e in edges))
        return {
            "stations":stations,"legs":legs,"interchanges":interchanges,
            "distance_km":round(distance,1),"stop_count":sum(max(0,l["stops"]) for l in legs),
            "interchange_count":len(interchanges),"estimated_minutes":minutes,
            "estimated_time_text":self._fmt(minutes),
            "fare_inr":self._fare(distance),
            "routing_basis":"2026 station/route feed; journey time is a planning estimate."
        }

    def _leg(self,ss,n):
        if not ss:return {}
        return {"number":n,"line":ss[0]["line"],"direction":self._direction(ss),
                "start_station":ss[0],"end_station":ss[-1],
                "stops":max(0,len(ss)-1),"stations":ss}

    def _direction(self,ss):
        if len(ss)<2:return "toward the destination"
        line=ss[0]["line"]
        # Use the line path endpoints for a human direction label.
        path=self.metro.line_paths.get(line,[])
        if not path:return "toward the destination"
        first=path[0]["name"]; last=path[-1]["name"]
        # If the next station occurs later in the display path, use its endpoint.
        names=[norm_name(x["name"]) for x in path]
        try:
            a=names.index(norm_name(ss[0]["name"])); b=names.index(norm_name(ss[1]["name"]))
            return f"toward {last if b>a else first}"
        except ValueError:
            return "toward the destination"

    @staticmethod
    def _fmt(m):
        return f"{m//60} hr {m%60:02d} min" if m>=60 else f"{m} min"
