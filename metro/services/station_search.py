
import re
from .data_loader import load_all_metro_data

def _norm(s):
    s=re.sub(r"[^a-z0-9 ]","",str(s).lower()).strip()
    aliases={"sahid sthal":"shaheed sthal new bus adda","shahid sthal":"shaheed sthal new bus adda",
             "shaheed sthal":"shaheed sthal new bus adda"}
    return aliases.get(s,s)

class StationSearch:
    _stations=None
    def __init__(self):
        if StationSearch._stations is None:
            df=load_all_metro_data()["primary"]
            out=[]
            for _,r in df.iterrows():
                out.append({"id":int(r["stop_id"]),"name":str(r["stop_name"]).strip(),
                            "line":str(r["route_names"]).split(",")[0].strip(),
                            "route_names":str(r["route_names"]),
                            "latitude":float(r["stop_lat"]),"longitude":float(r["stop_lon"]),
                            "first_arrival":str(r.get("first_arrival","")),
                            "last_departure":str(r.get("last_departure",""))})
            StationSearch._stations=out
    def search(self,query,top_k=10):
        q=_norm(query)
        if not q:return []
        scored=[]
        for s in self._stations:
            n=_norm(s["name"])
            tokens=set(q.split())
            overlap=len(tokens & set(n.split()))
            score=1000 if n==q else 800 if n.startswith(q) else 600 if q in n else 100+overlap*50
            if score>=150: scored.append((score,s))
        scored.sort(key=lambda x:(-x[0],x[1]["name"]))
        return [s for _,s in scored[:top_k]]
