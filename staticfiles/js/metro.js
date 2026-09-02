const stations=window.METRO_STATIONS||[];
const map=L.map("metroMap",{zoomControl:true,maxBounds:[[27.85,76.70],[29.20,77.70]],maxBoundsViscosity:.9}).setView([28.6139,77.209],11);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{maxZoom:19,attribution:"© OpenStreetMap contributors"}).addTo(map);

const colors={"Red line":"#ef233c","Red Line":"#ef233c","Yellow line":"#f2c94c","Yellow Line":"#f2c94c","Blue line":"#2563eb","Blue Line":"#2563eb","Green line":"#16a34a","Green Line":"#16a34a","Violet line":"#7c3aed","Violet Line":"#7c3aed","Pink line":"#ec4899","Pink Line":"#ec4899","Magenta line":"#d946ef","Magenta Line":"#d946ef","Gray line":"#6b7280","Grey line":"#6b7280","Orange line":"#f97316","Orange Line":"#f97316","Aqua line":"#0891b2","Aqua Line":"#0891b2","Rapid Metro":"#14b8a6"};
const lineColor=l=>colors[l]||"#334155";

const groups={};
stations.forEach(s=>{
  const line=s.route_names?.split(",")[0]||"Metro";
  (groups[line]??=[]).push(s);
});
const linePaths=window.METRO_LINE_PATHS||{};
const displayGroups={};
Object.entries(linePaths).forEach(([line,arr])=>{
  if(arr.length<2)return;
  displayGroups[line]=arr;
  L.polyline(arr.map(s=>[s.latitude,s.longitude]),{color:lineColor(line),weight:6,opacity:.86}).addTo(map);
});
stations.forEach(s=>{
  const lines=(s.route_names||"").split(",").map(x=>x.split("_")[0]).filter(Boolean);
  const label=[...new Set(lines)].join(" · ");
  L.circleMarker([s.latitude,s.longitude],{radius:3,color:"#fff",weight:1.5,fillColor:lineColor(label.includes("RED")?"Red Line":label.includes("YELLOW")?"Yellow Line":label.includes("BLUE")?"Blue Line":"#334155"),fillOpacity:1})
    .addTo(map).bindTooltip(`${escapeHtml(s.name)}<br><small>${escapeHtml(label)}</small>`);
});
document.getElementById("lineLegend").innerHTML=`<div class="legend-grid">${Object.keys(displayGroups).map(l=>`<div class="legend-item"><i class="line-dot" style="background:${lineColor(l)}"></i>${escapeHtml(l)}</div>`).join("")}</div>`;

let start=null,end=null,routeLayers=[],userMarker=null,routeMarkers=[];
function togglePanel(){document.querySelector(".metro-panel").classList.toggle("closed")}
function escapeHtml(s){return String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]))}

function searchStations(q,box,cb){
  if(q.length<2){box.classList.remove("show");return}
  fetch(`/metro/stations/?q=${encodeURIComponent(q)}`).then(r=>r.json()).then(d=>{
    const results=d.results||[];
    box.innerHTML=results.map((s,i)=>`<div class="suggestion" data-i="${i}"><b>${escapeHtml(s.name)}</b><small>${escapeHtml(s.line)}</small></div>`).join("")||
      `<div class="suggestion"><b>No station found</b><small>Try "Shaheed Sthal" or "Rajiv Chowk"</small></div>`;
    box.classList.add("show");
    box.querySelectorAll(".suggestion[data-i]").forEach(el=>el.onclick=()=>{cb(results[Number(el.dataset.i)]);box.classList.remove("show")});
  }).catch(()=>{box.innerHTML=`<div class="suggestion"><b>Search temporarily unavailable</b></div>`;box.classList.add("show")});
}
document.getElementById("startStation").oninput=e=>searchStations(e.target.value,document.getElementById("startSuggestions"),s=>{start=s;e.target.value=s.name});
document.getElementById("endStation").oninput=e=>searchStations(e.target.value,document.getElementById("endSuggestions"),s=>{end=s;e.target.value=s.name});

function swapStations(){
  [start,end]=[end,start];
  document.getElementById("startStation").value=start?.name||"";
  document.getElementById("endStation").value=end?.name||"";
}
function clearRouteLayers(){
  routeLayers.forEach(x=>map.removeLayer(x)); routeLayers=[];
  routeMarkers.forEach(x=>map.removeLayer(x)); routeMarkers=[];
}

function drawMetroRoute(route){
  clearRouteLayers();
  route.legs.forEach((leg,idx)=>{
    const pts=leg.stations.map(s=>[s.latitude,s.longitude]);
    if(pts.length<2)return;
    routeLayers.push(L.polyline(pts,{color:lineColor(leg.line),weight:10,opacity:.25}).addTo(map));
    routeLayers.push(L.polyline(pts,{color:lineColor(leg.line),weight:6,opacity:.98}).addTo(map));
    const mid=pts[Math.floor(pts.length/2)];
    const label=L.circleMarker(mid,{radius:9,color:"#fff",weight:2,fillColor:lineColor(leg.line),fillOpacity:1})
      .addTo(map).bindTooltip(`${escapeHtml(leg.line)} · ${leg.stops} stop(s)`);
    routeMarkers.push(label);
  });

  routeMarkers.push(L.marker([route.stations[0].latitude,route.stations[0].longitude]).addTo(map)
    .bindPopup(`<b>START</b><br>${escapeHtml(route.stations[0].name)}`).openPopup());
  routeMarkers.push(L.marker([route.stations.at(-1).latitude,route.stations.at(-1).longitude]).addTo(map)
    .bindPopup(`<b>DESTINATION</b><br>${escapeHtml(route.stations.at(-1).name)}`));

  route.interchanges.forEach((x,i)=>{
    const m=L.circleMarker([route.stations[x.step_index].latitude,route.stations[x.step_index].longitude],{
      radius:12,color:"#111827",weight:3,fillColor:"#f59e0b",fillOpacity:1
    }).addTo(map);
    m.bindPopup(`<b>Interchange ${i+1}</b><br>${escapeHtml(x.station_name)}<br>${escapeHtml(x.from_line)} → ${escapeHtml(x.to_line)}`);
    routeMarkers.push(m);
  });

  const bounds=L.latLngBounds(route.stations.map(s=>[s.latitude,s.longitude]));
  map.fitBounds(bounds,{padding:[70,70]});
}

function legCard(leg){
  return `<div class="leg-card" style="--line:${lineColor(leg.line)}">
    <div class="leg-top"><span class="line-badge">${escapeHtml(leg.line)}</span><b>Leg ${leg.number}</b><span>${leg.stops} stop(s)</span></div>
    <h4>Board at ${escapeHtml(leg.start_station.name)}</h4>
    <p class="direction">↗ Stay on this line ${escapeHtml(leg.direction)}</p>
    <div class="leg-route">${leg.stations.map((s,i)=>`<span class="${i===0||i===leg.stations.length-1?'strong':''}">${escapeHtml(s.name)}</span>`).join("<i>›</i>")}</div>
    <p class="leg-end">Get down at <b>${escapeHtml(leg.end_station.name)}</b>${leg.number===1&&leg.stops?` after ${leg.stops} stop(s)`:''}</p>
  </div>`;
}

function interchangeCard(x,i){
  const steps=(x.steps||[]).map((s,n)=>`<li>${escapeHtml(s)}</li>`).join("");
  return `<div class="interchange-card">
    <div class="change-number">${i+1}</div>
    <div><b>Change at ${escapeHtml(x.station_name)}</b>
      <div class="change-lines"><span style="background:${lineColor(x.from_line)}">${escapeHtml(x.from_line)}</span><strong>→</strong><span style="background:${lineColor(x.to_line)}">${escapeHtml(x.to_line)}</span></div>
      <p><b>Transfer estimate:</b> ${x.walk_m||250} m · ${x.walk_min||4} min · indoor transfer.</p>
      <ol class="transfer-steps">${steps}</ol>
    </div>
  </div>`;
}

async function findMetroRoute(){
  if(!start||!end){alert("Choose both metro stations.");return}
  const box=document.getElementById("routeResult");
  box.innerHTML="<div class='route-card loading'>Calculating the complete station-by-station path…</div>";
  try{
    const d=await fetch(`/metro/route/?start=${encodeURIComponent(start.name)}&destination=${encodeURIComponent(end.name)}`).then(r=>r.json());
    if(!d.success)throw new Error(d.error||"No metro route found.");
    drawMetroRoute(d.route);

    const interchanges=d.route.interchanges||[];
    box.innerHTML=`
      <div class="route-card">
        <div class="route-title"><div><small>METRO JOURNEY</small><h3>${escapeHtml(d.from.name)} → ${escapeHtml(d.to.name)}</h3></div><span class="route-ok">✓ Connected</span></div>
        <div class="route-meta">
          <span class="pill">${d.route.stop_count} stops</span>
          <span class="pill">${d.route.distance_km} km</span>
          <span class="pill">~${d.route.estimated_time_text}</span>
          ${d.route.fare_inr?`<span class="pill fare">₹${d.route.fare_inr} est. fare</span>`:""}
          <span class="pill ${interchanges.length?'warn':''}">${interchanges.length} interchange${interchanges.length===1?'':'s'}</span>
        </div>
        <div class="notice">⏱ ${escapeHtml(d.note||"Time is an estimate.")}</div>

        <div class="section-title">YOUR EXACT PLAN</div>
        ${d.route.legs.map(legCard).join("")}

        ${interchanges.length?`<div class="section-title change-heading">INTERCHANGE DETAILS</div>${interchanges.map(interchangeCard).join("")}`:"<div class='direct-card'>Direct ride — no line change required.</div>"}

        <div class="section-title">STATION-BY-STATION</div>
        <div class="station-list">${d.route.stations.map((s,i)=>`<div class="station-row">
          <span class="station-no">${i+1}</span><i class="line-dot" style="background:${lineColor(s.line)}"></i>
          <span>${escapeHtml(s.name)}</span><small>${escapeHtml(s.line)}</small>
        </div>`).join("")}</div>

        <div class="exit-card"><b>Final step</b><br>Get down at <strong>${escapeHtml(d.to.name)}</strong>. After leaving the metro, use the road map's walking mode for the final destination if needed.</div>
      </div>`;
  }catch(e){box.innerHTML=`<div class="route-card error"><b>Metro route failed</b><p>${escapeHtml(e.message)}</p></div>`}
}

function distanceKm(a,b,c,d){const R=6371,p=Math.PI/180,x=(c-a)*p,y=(d-b)*p;return 2*R*Math.asin(Math.sqrt(Math.sin(x/2)**2+Math.cos(a*p)*Math.cos(c*p)*Math.sin(y/2)**2))}

function useGPS(){
  if(!navigator.geolocation)return alert("Location is not supported.");
  navigator.geolocation.getCurrentPosition(async p=>{
    const lat=p.coords.latitude,lon=p.coords.longitude;
    let nearest=stations.map(s=>({...s,d:(s.latitude-lat)**2+(s.longitude-lon)**2})).sort((a,b)=>a.d-b.d)[0];
    if(nearest){
      const dist=distanceKm(lat,lon,nearest.latitude,nearest.longitude);
      nearest.distance_km=dist;
      start=nearest;
      document.getElementById("startStation").value=nearest.name;
      document.getElementById("nearestStationCard").innerHTML=`<small>NEAREST METRO</small><b>${escapeHtml(nearest.name)}</b><span>${dist<1?Math.round(dist*1000)+" m":dist.toFixed(1)+" km"} away · estimated road-side distance may vary</span>`;
      map.setView([lat,lon],14);
      if(userMarker)map.removeLayer(userMarker);
      userMarker=L.circleMarker([lat,lon],{radius:8,color:"#fff",weight:3,fillColor:"#2857bd",fillOpacity:1}).addTo(map).bindPopup(`<b>Your location</b><br>Nearest station: ${escapeHtml(nearest.name)}<br>${dist.toFixed(1)} km away`).openPopup();
    }
  },()=>alert("Please allow location access."));
}
setTimeout(()=>map.invalidateSize(),300);
