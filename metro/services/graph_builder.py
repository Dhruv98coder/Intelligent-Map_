
import re, math
import numpy as np
from collections import defaultdict
from .data_loader import load_all_metro_data

LINE_DISPLAY = {
    "RED":"Red Line","BLUE":"Blue Line","YELLOW":"Yellow Line","GREEN":"Green Line",
    "VIOLET":"Violet Line","PINK":"Pink Line","MAGENTA":"Magenta Line",
    "AQUA":"Aqua Line","RAPID":"Rapid Metro","ORANGE/AIRPORT":"Airport Express",
    "GRAY":"Grey Line","GREY":"Grey Line"
}

def norm_name(s):
    s = str(s or "").lower()
    s = re.sub(r"\[conn:[^\]]+\]", "", s, flags=re.I)
    s = re.sub(r"\(new bus adda\)", "new bus adda", s, flags=re.I)
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    aliases = {
        "sahid sthal":"shaheed sthal new bus adda",
        "shahid sthal":"shaheed sthal new bus adda",
        "shaheed sthal":"shaheed sthal new bus adda",
        "huda city center":"huda city centre",
        "guru dhronacharya":"guru dronacharya",
    }
    return aliases.get(s, s)

def haversine_km(a_lat,a_lon,b_lat,b_lon):
    R=6371.0088
    p=math.pi/180
    x=(b_lat-a_lat)*p; y=(b_lon-a_lon)*p
    q=math.sin(x/2)**2+math.cos(a_lat*p)*math.cos(b_lat*p)*math.sin(y/2)**2
    return R*2*math.atan2(math.sqrt(q),math.sqrt(1-q))

class MetroGraph:
    """
    Builds the metro graph from the new 2026 station/route dataset only.
    Route ordering is recovered from each directional route's station geometry
    (PCA projection) and endpoint names. No legacy station edges are imported.
    """
    def __init__(self):
        data=load_all_metro_data()
        self.df=data["primary"].copy()
        self.fares=data["fares"].copy()
        self.stations={}
        self.line_stations=defaultdict(set)
        self.graph=defaultdict(list)
        self.line_paths=defaultdict(list)
        self.interchange_details={}
        self._build()

    def _build(self):
        df=self.df
        for _,r in df.iterrows():
            sid=int(r["stop_id"])
            self.stations[sid]={
                "id":sid,"name":str(r["stop_name"]).strip(),
                "latitude":float(r["stop_lat"]),"longitude":float(r["stop_lon"]),
                "route_ids":str(r.get("route_ids","")),
                "route_names":str(r.get("route_names","")),
                "first_arrival":str(r.get("first_arrival","")),
                "last_departure":str(r.get("last_departure","")),
                "service_ids":str(r.get("service_ids","")),
            }

        # `route_ids` in the supplied station-level file is not a positional
        # pairing with `route_long_names`; the same numeric IDs are reused in
        # the aggregated station lists. Therefore routing is built from the
        # complete route_long_names strings instead of guessing ID/name pairs.
        route_members=defaultdict(list)
        for _,r in df.iterrows():
            sid=int(r["stop_id"])
            for route_label in [x.strip() for x in str(r.get("route_long_names","")).split(",") if x.strip()]:
                route_members[route_label].append(sid)

        # Recover each directional route's stop order from geometry, orienting
        # it to the named first endpoint. Edges are then unioned by line.
        for route_label, ids in route_members.items():
            ids=list(dict.fromkeys(ids))
            if len(ids)<2: continue
            pts=np.array([[self.stations[s]["longitude"],self.stations[s]["latitude"]] for s in ids])
            center=pts.mean(axis=0)
            _,_,vh=np.linalg.svd(pts-center,full_matrices=False)
            axis=vh[0]
            proj=(pts-center)@axis
            order=[sid for _,sid in sorted(zip(proj,ids))]
            suffix=route_label.split("_",1)[1] if "_" in route_label else route_label
            ends=re.split(r"\s+to\s+",suffix,flags=re.I)
            if len(ends)==2:
                first=norm_name(ends[0])
                def similarity(a,b):
                    aa=set(norm_name(a).split()); bb=set(b.split())
                    return (len(aa&bb)/(len(aa|bb) or 1)) + (0.4 if b in norm_name(a) or norm_name(a) in b else 0)
                if similarity(self.stations[order[-1]]["name"],first)>similarity(self.stations[order[0]]["name"],first):
                    order.reverse()
            line_code=(route_label.split("_",1)[0] if "_" in route_label else route_label).strip().upper()
            line=LINE_DISPLAY.get(line_code,line_code.title())
            for sid in order: self.line_stations[line].add(sid)
            if len(order)>len(self.line_paths[line]):
                self.line_paths[line]=[self.stations[s] for s in order]
            for a,b in zip(order,order[1:]):
                if a==b: continue
                d=haversine_km(self.stations[a]["latitude"],self.stations[a]["longitude"],self.stations[b]["latitude"],self.stations[b]["longitude"])
                self._add_edge((a,line),(b,line),d,"ride")
                self._add_edge((b,line),(a,line),d,"ride")

        # Transfer edges. A station can carry several line labels in the new feed.
        for sid, lineset in ((sid, [l for l,sids in self.line_stations.items() if sid in sids])
                              for sid in self.stations):
            lines=sorted(set(lineset))
            if len(lines)<2: continue
            pairs=[]
            for i,a in enumerate(lines):
                for b in lines[i+1:]:
                    detail=self._interchange_detail(sid,a,b)
                    pairs.append(detail)
                    self._add_edge((sid,a),(sid,b),0.0,"transfer",detail)
                    self._add_edge((sid,b),(sid,a),0.0,"transfer",detail)
            self.interchange_details[sid]=pairs

    def _add_edge(self,u,v,d,kind,detail=None):
        item={"to":v,"distance_km":d,"type":kind}
        if detail: item["detail"]=detail
        self.graph[u].append(item)

    def _interchange_detail(self,sid,a,b):
        # Static feed does not contain indoor geometry/platform/gate coordinates.
        # Give a transparent planning estimate rather than inventing a precise path.
        mins=4
        walk_m=250
        return {
            "station_id":sid,
            "station_name":self.stations[sid]["name"],
            "from_line":a,"to_line":b,
            "estimated_walk_m":walk_m,
            "estimated_walk_min":mins,
            "indoor_walk":True,
            "steps":[
                f"Get off the {a} train at {self.stations[sid]['name']}.",
                f"Follow interchange signs for the {b}.",
                "Walk through the transfer concourse and follow platform signs.",
                f"Allow about {mins} min / {walk_m} m for the transfer (planning estimate).",
                "Platform/gate-level indoor geometry is not present in the supplied feed; verify station signage."
            ]
        }

    def get_station(self,sid):
        return self.stations.get(int(sid))

    def find_station(self,name):
        q=norm_name(name)
        for s in self.stations.values():
            if norm_name(s["name"])==q: return s
        return None

    def all_stations(self):
        return list(self.stations.values())
