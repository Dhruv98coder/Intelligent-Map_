/* GoPlan IntelligentMap — fast NCR search + stable live road navigation */
const NCR_BOUNDS=[[27.05,75.85],[29.85,78.70]];
const NCR_CENTER=[28.6139,77.2090];
const NCR_VIEW_PAD=0.08;
const NCR_MAX_BOUNDS=[[NCR_BOUNDS[0][0]-NCR_VIEW_PAD,NCR_BOUNDS[0][1]-NCR_VIEW_PAD],[NCR_BOUNDS[1][0]+NCR_VIEW_PAD,NCR_BOUNDS[1][1]+NCR_VIEW_PAD]];
let map=L.map("map",{zoomControl:false,maxBounds:NCR_MAX_BOUNDS,maxBoundsViscosity:0.88,minZoom:9}).setView(NCR_CENTER,11);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{maxZoom:19,attribution:"© OpenStreetMap contributors"}).addTo(map);
L.control.zoom({position:"bottomright"}).addTo(map);

let mode="car",currentPosition=null,watchId=null,fromLocation=null,toLocation=null;
let routeLayers=[],markers=[],currentMarker=null,destinationMarker=null,navLine=null,activeRoute=null,navTimer=null,lastNavReroute=null,navStepIndex=0,lastSpokenStep=-1;
<<<<<<< HEAD
let rerouteBusy=false,lastRerouteAt=0,searchTimer=null,searchController=null,weatherRequestSerial=0,lastRerouteOrigin=null;
const ROUTE_OFFROAD_KM=0.035; // ~35 m off the active road before rerouting
const REROUTE_COOLDOWN_MS=2800;
const REROUTE_MIN_MOVE_KM=0.020; // don't reroute again unless user has moved ~20 m
const NAV_UPDATE_MS=1000;
=======
let rerouteBusy=false,lastRerouteAt=0,searchTimer=null,searchController=null,weatherRequestSerial=0;
const ROUTE_OFFROAD_KM=0.045; // ~45 m off the active road before rerouting
const REROUTE_COOLDOWN_MS=4500;
>>>>>>> 18b97f5c09e78b2c0578622a3fd9d3bbb52bf3b5
const API={search:document.body.dataset.searchUrl,route:document.body.dataset.routeUrl,smartConnect:document.body.dataset.smartConnectUrl,weather:document.body.dataset.weatherUrl,nearby:document.body.dataset.nearbyUrl,awareness:document.body.dataset.awarenessUrl,train:document.body.dataset.trainUrl};

function csrfToken(){const m=document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);return m?decodeURIComponent(m[1]):""}
function apiUrl(base,params={}){const u=new URL(base,location.origin);Object.entries(params).forEach(([k,v])=>u.searchParams.set(k,v));return u.toString()}
function togglePanel(id){document.getElementById(id)?.classList.toggle("hidden")}
function toggleSearchBox(){
 const box=document.getElementById("routeSearchBox"),btn=document.getElementById("searchToggleBtn"),text=document.getElementById("searchToggleText");
 if(!box||!btn)return;
 const hidden=box.classList.toggle("search-collapsed");
 btn.classList.toggle("is-open",!hidden);
 btn.setAttribute("aria-expanded",String(!hidden));
 if(text)text.textContent=hidden?"Show search":"Hide search";
 if(!hidden){setTimeout(()=>document.getElementById("toInput")?.focus(),120)}
}
function closePanel(id){document.getElementById(id)?.classList.add("hidden")}
function openMetro(){location.href="/metro/"}
function setMode(m){mode=m;document.querySelectorAll(".mode,.mode-mini").forEach(b=>b.classList.toggle("active",b.dataset.mode===m));if(m==="train"){togglePanel("trainPanel");loadTrainSchedule()}}
function clearSearch(){document.getElementById("toInput").value="";document.getElementById("toSuggestions").classList.remove("show")}
function focusRouteSearch(id){document.getElementById(id)?.focus()}
function pin(p,color="#ef4444"){return L.circleMarker([p.latitude,p.longitude],{radius:8,color:"#fff",weight:3,fillColor:color,fillOpacity:1}).addTo(map)}
function clearRoute(){routeLayers.forEach(x=>map.removeLayer(x));routeLayers=[];if(navLine){map.removeLayer(navLine);navLine=null}if(destinationMarker){map.removeLayer(destinationMarker);destinationMarker=null}activeRoute=null}
function useCurrentLocation(){if(currentPosition){setFromLocation({...currentPosition,name:"Current location"});return}locateMe(true)}
function setFromLocation(p){fromLocation=p;document.getElementById("fromInput").value=p.name||"Current location"}
function swapLocations(){const a=fromLocation,b=toLocation;if(b)setFromLocation(b);else{fromLocation=null;document.getElementById("fromInput").value=""}if(a){toLocation=a;document.getElementById("toInput").value=a.name||"Current location";pinDestination(a)}else{toLocation=null;document.getElementById("toInput").value=""}if(toLocation)fetchDestinationWeather()}

function locateMe(force=false){
 if(!navigator.geolocation){alert("Location is not supported by this browser.");return}
 navigator.geolocation.getCurrentPosition(pos=>{updateLocation(pos);if(force)setFromLocation({...currentPosition,name:"Current location"});map.setView([pos.coords.latitude,pos.coords.longitude],15)},()=>alert("Location permission is needed for live navigation."),{enableHighAccuracy:true,timeout:10000,maximumAge:3000});
 if(!watchId)watchId=navigator.geolocation.watchPosition(updateLocation,()=>{}, {enableHighAccuracy:true,maximumAge:1500,timeout:10000});
}
function updateLocation(pos){
 currentPosition={latitude:pos.coords.latitude,longitude:pos.coords.longitude,accuracy:pos.coords.accuracy||999,speed:pos.coords.speed,heading:pos.coords.heading};
 if(!currentMarker)currentMarker=L.circleMarker([currentPosition.latitude,currentPosition.longitude],{radius:8,color:"#fff",weight:3,fillColor:"#2563eb",fillOpacity:1}).addTo(map).bindTooltip("You");else currentMarker.setLatLng([currentPosition.latitude,currentPosition.longitude]);
 if(document.getElementById("navHud")&&!document.getElementById("navHud").classList.contains("hidden")){updateNavHUD();checkOffRouteAndReroute()}
 if(document.getElementById("weatherPanel")&&!document.getElementById("weatherPanel").classList.contains("hidden"))fetchWeather(currentPosition.latitude,currentPosition.longitude);
}

async function geocodeInput(q,box,callback,remote=false){
 if(q.toLowerCase().includes("current location")&&currentPosition){callback([{name:"Current location",display_name:"GPS position",latitude:currentPosition.latitude,longitude:currentPosition.longitude}]);return}
 if(searchController)searchController.abort();searchController=new AbortController();
 try{const r=await fetch(apiUrl(API.search,{q,remote:remote?"1":"0"}),{headers:{Accept:"application/json"},signal:searchController.signal});const d=r.ok?await r.json():{results:[]};callback(d.results||[])}catch(e){if(e.name!=="AbortError")callback([])}
}
function showResults(box,results,onClick){
 box.innerHTML=results.map((r,i)=>`<div class="suggestion" data-i="${i}"><b>${escapeHtml(r.name)}</b><small>${escapeHtml(r.display_name||r.category||"Delhi NCR")}</small><em>${escapeHtml(r.source||"Mapped place")}</em></div>`).join("")||`<div class="suggestion"><b>No place found</b><small>Try a road, colony, market, village, landmark, station, hotel or city in Delhi NCR.</small></div>`;
 box.classList.add("show");box.querySelectorAll(".suggestion").forEach((el,i)=>{if(results[i])el.onclick=()=>{onClick(results[i]);box.classList.remove("show")}})
}
function selectPlace(inputId,x){
 const safeName=x.name||x.display_name?.split(",")[0]||"Selected place";
 const point={latitude:Number(x.latitude),longitude:Number(x.longitude),name:safeName};
 if(!Number.isFinite(point.latitude)||!Number.isFinite(point.longitude))return;
 if(inputId==="fromInput")setFromLocation(point);else{toLocation=point;document.getElementById("toInput").value=safeName;pinDestination(point);map.setView([point.latitude,point.longitude],16);fetchDestinationWeather()}
}
function pinDestination(x){if(destinationMarker)map.removeLayer(destinationMarker);destinationMarker=pin(x);return destinationMarker}
function escapeHtml(s){return String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]))}

function localSearchInput(inputId,boxId){
 const el=document.getElementById(inputId),box=document.getElementById(boxId);if(!el||!box)return;
 el.addEventListener("input",e=>{
   const q=e.target.value.trim();clearTimeout(searchTimer);
   if(q.length<2){box.classList.remove("show");return}
   searchTimer=setTimeout(()=>{
     geocodeInput(q,box,results=>{
       showResults(box,results,x=>selectPlace(inputId,x));
       if(results.length<4&&q.length>=3){
         setTimeout(()=>geocodeInput(q,box,remoteResults=>{if(remoteResults.length)showResults(box,remoteResults,x=>selectPlace(inputId,x))},true),260);
       }
     },false)
   },120)
 });
 el.addEventListener("keydown",e=>{if(e.key==="Enter"){
   e.preventDefault();const q=el.value.trim();if(q.length<2)return;
   box.innerHTML='<div class="suggestion"><b>Searching Delhi NCR…</b><small>Finding the best road, landmark, station or place.</small></div>';box.classList.add("show");
   geocodeInput(q,box,r=>showResults(box,r,x=>selectPlace(inputId,x)),true)
 }})
}
localSearchInput("fromInput","fromSuggestions");localSearchInput("toInput","toSuggestions");

function getRouteLocations(){if(!fromLocation&&currentPosition)setFromLocation({...currentPosition,name:"Current location"});return fromLocation&&toLocation}
async function findRoute(){
 if(mode==="metro"){openMetro();return}if(mode==="train"){togglePanel("trainPanel");loadTrainSchedule();return}
 if(!getRouteLocations()){alert("Set both From and To. Use GPS for the current location.");return}
 clearRoute();const btn=document.querySelector(".find-mini");if(btn){btn.disabled=true;btn.textContent="Finding…"}
 try{const res=await fetch(API.route,{method:"POST",headers:{"Content-Type":"application/json","X-CSRFToken":csrfToken()},body:JSON.stringify({from:fromLocation,to:toLocation,mode})});const data=await res.json();if(!data.success)throw new Error(data.error||"Route failed");
  window.lastRoutes=data.routes||[data.route];activeRoute=data.route||data.routes[0];drawRoutes(window.lastRoutes);showSummary(activeRoute);showSteps(activeRoute);document.getElementById("startNavBtn").classList.remove("hidden");document.getElementById("routePanel").classList.remove("hidden");
  pinDestination(toLocation);map.fitBounds(L.geoJSON(activeRoute.geometry).getBounds(),{padding:[55,120]});fetchAwareness();fetchSmartConnect();
 }catch(e){alert(e.message)}finally{if(btn){btn.disabled=false;btn.textContent="Find route →"}}
}
function drawRoutes(routes){
 routes.forEach((r,i)=>{const layer=L.geoJSON(r.geometry,{style:{weight:i===0?4:3,opacity:i===0?.9:.35,color:i===0?"#2563eb":"#64748b",dashArray:i===0?null:"7 9",lineCap:"round",lineJoin:"round"}}).addTo(map);layer.on("click",()=>{activeRoute=r;showSummary(r);showSteps(r)});routeLayers.push(layer)})
}
function showSummary(r){document.getElementById("routeSummary").classList.remove("hidden");document.getElementById("summaryDistance").textContent=r.distance_text;document.getElementById("summaryDuration").textContent=r.duration_text;document.getElementById("summaryArrival").textContent=new Date(Date.now()+r.duration_minutes*60000).toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"});const box=document.getElementById("routeOptions");box.innerHTML=(window.lastRoutes||[r]).map((x,i)=>`<div class="route-option"><span>${i===0?"Recommended":"Alternative "+i} · ${x.distance_text} · ${x.duration_text}</span><button onclick="selectRoute(${i})">Use</button></div>`).join("")}
function selectRoute(i){if(!window.lastRoutes?.[i])return;activeRoute=window.lastRoutes[i];routeLayers.forEach(x=>map.removeLayer(x));routeLayers=[];drawRoutes(window.lastRoutes);showSummary(activeRoute);showSteps(activeRoute)}
async function fetchSmartConnect(){
 const panel=document.getElementById("smartConnect"),body=document.getElementById("smartConnectBody");
 if(!panel||!fromLocation||!toLocation||!activeRoute)return;
 panel.classList.remove("hidden");body.innerHTML='<div class="connect-note">Finding a practical last-mile option near the road…</div>';
 try{
   const d=await fetch(apiUrl(API.smartConnect,{from_lat:fromLocation.latitude,from_lon:fromLocation.longitude,to_lat:toLocation.latitude,to_lon:toLocation.longitude,distance_km:activeRoute.distance_km})).then(r=>r.json());
   if(!d.success)throw new Error(d.error||"Unavailable");
   const a=d.origin_stop||{},b=d.destination_stop||{};
   body.innerHTML=`
    <div class="connect-leg"><div class="connect-icon">🛺</div><div class="connect-copy"><b>Auto pickup → ${escapeHtml(a.name||"nearest bus stop")}</b><span>${a.distance_m?`${a.distance_m} m from your start · estimated pickup`:"Nearby pickup point"}</span></div><div class="connect-fare">₹${Number(d.auto_fare||0)}</div></div>
    <div class="connect-leg"><div class="connect-icon">🚌</div><div class="connect-copy"><b>Bus → ${escapeHtml(b.name||"destination-side stop")}</b><span>${escapeHtml(d.bus_text||"Suggested bus corridor · estimated fare")}</span></div><div class="connect-fare">₹${Number(d.bus_fare||0)}</div></div>
    <div class="connect-leg"><div class="connect-icon">🚶</div><div class="connect-copy"><b>Walk → final destination</b><span>${b.distance_m?`${b.distance_m} m from the destination-side stop`:"Short final walk"}</span></div><div class="connect-fare">Free</div></div>
    <div class="connect-total"><span>Estimated total</span><b>₹${Number(d.total_fare||0)} · ${escapeHtml(d.total_time_text||"")}</b></div>
    <div class="connect-note">Fare and bus leg are estimates. Live bus-line matching requires Delhi bus/GTFS live data; GoPlan will not present an estimate as a live departure.</div>`;
 }catch(e){body.innerHTML='<div class="connect-note">Smart Connect is unavailable right now. You can still use the road, metro or walking route above.</div>'}
}

function showSteps(r){const p=document.getElementById("stepsPanel"),box=document.getElementById("routeSteps");p.classList.remove("hidden");box.innerHTML=(r.steps||[]).map((s,i)=>`<div class="step"><b>${i+1}. ${escapeHtml(s.instruction)}</b><small>${s.distance_m>=1000?(s.distance_m/1000).toFixed(1)+" km":s.distance_m+" m"} · ${s.duration_min} min</small></div>`).join("")}

/* Find the closest point on the actual GeoJSON road, not a straight line to destination. */
function nearestPointOnRoute(route,lat,lon){
 const coords=route?.geometry?.coordinates||[];if(coords.length<2)return null;let best={distance:Infinity,index:0,t:0,lat:coords[0][1],lon:coords[0][0]};
 for(let i=0;i<coords.length-1;i++){const a=coords[i],b=coords[i+1];const refLat=(a[1]+b[1])/2;const x=(b[0]-a[0])*Math.cos(refLat*Math.PI/180),y=b[1]-a[1];const px=(lon-a[0])*Math.cos(refLat*Math.PI/180),py=lat-a[1];const den=x*x+y*y||1;let t=(px*x+py*y)/den;t=Math.max(0,Math.min(1,t));const qLon=a[0]+(b[0]-a[0])*t,qLat=a[1]+(b[1]-a[1])*t;const d=_haversine(lat,lon,qLat,qLon);if(d<best.distance)best={distance:d,index:i,t,lat:qLat,lon:qLon}}
 return best;
}
<<<<<<< HEAD
function cumulativeRouteDistances(route){
 const coords=route?.geometry?.coordinates||[]; const d=[0];
 for(let i=1;i<coords.length;i++) d.push(d[i-1]+_haversine(coords[i-1][1],coords[i-1][0],coords[i][1],coords[i][0]));
 return d;
}
function remainingRouteDistanceKm(route,lat,lon){
 const coords=route?.geometry?.coordinates||[];if(coords.length<2)return 0;
 const n=nearestPointOnRoute(route,lat,lon);if(!n)return route.distance_km||0;
 const cum=cumulativeRouteDistances(route);const a=coords[n.index],b=coords[n.index+1];
 const seg=_haversine(a[1],a[0],b[1],b[0]);
 const fromA=seg*n.t;
 const doneKm=(cum[n.index]||0)+fromA;
 return Math.max(0,(cum[cum.length-1]||0)-doneKm);
}
=======
>>>>>>> 18b97f5c09e78b2c0578622a3fd9d3bbb52bf3b5
function remainingRouteGeometry(route,lat,lon){
 const coords=route?.geometry?.coordinates||[];if(coords.length<2)return route?.geometry;const n=nearestPointOnRoute(route,lat,lon);if(!n)return route.geometry;const out=[[n.lon,n.lat],...coords.slice(n.index+1)];return {type:"LineString",coordinates:out};
}
function checkOffRouteAndReroute(){
<<<<<<< HEAD
 if(!currentPosition||!activeRoute||rerouteBusy)return;
 const nearest=nearestPointOnRoute(activeRoute,currentPosition.latitude,currentPosition.longitude);if(!nearest)return;
 const movedSinceReroute=lastRerouteOrigin?_haversine(currentPosition.latitude,currentPosition.longitude,lastRerouteOrigin.latitude,lastRerouteOrigin.longitude):Infinity;
 if(nearest.distance>ROUTE_OFFROAD_KM && Date.now()-lastRerouteAt>REROUTE_COOLDOWN_MS && movedSinceReroute>=REROUTE_MIN_MOVE_KM)rerouteLive();
}
async function rerouteLive(){
 if(!currentPosition||!toLocation||!activeRoute||rerouteBusy)return;rerouteBusy=true;lastRerouteAt=Date.now();lastRerouteOrigin={...currentPosition};
 const notice=document.getElementById("awarenessText");if(notice)notice.textContent="Re-routing from your current road…";
 try{const r=await fetch(API.route,{method:"POST",headers:{"Content-Type":"application/json","X-CSRFToken":csrfToken()},body:JSON.stringify({from:currentPosition,to:toLocation,mode})}).then(x=>x.json());if(r.success){window.lastRoutes=r.routes||[r.route];activeRoute=r.route||r.routes[0];navStepIndex=0;lastSpokenStep=-1;routeLayers.forEach(x=>map.removeLayer(x));routeLayers=[];drawRoutes(window.lastRoutes);showSteps(activeRoute);updateNavHUD();if(notice)notice.textContent="Route updated for your new road."}}
 catch(e){if(notice)notice.textContent="Keeping your current route — reroute service is temporarily unavailable."}finally{rerouteBusy=false}
}
function startNavigation(){
 if(!currentPosition){locateMe(true);setTimeout(()=>startNavigation(),1200);return}if(!activeRoute){alert("Find a route first.");return}
 document.getElementById("navHud").classList.remove("hidden");lastNavReroute={...currentPosition};lastRerouteAt=Date.now();lastRerouteOrigin={...currentPosition};navStepIndex=0;lastSpokenStep=-1;document.getElementById("navDestination").textContent=toLocation?.name||"Destination";document.getElementById("routePanel").classList.add("hidden");
 updateNavHUD();if(!watchId)locateMe();if(navTimer)clearInterval(navTimer);navTimer=setInterval(()=>{updateNavHUD();speakNextManeuver()},NAV_UPDATE_MS);speakNextManeuver();
=======
 if(!currentPosition||!activeRoute||rerouteBusy)return;const nearest=nearestPointOnRoute(activeRoute,currentPosition.latitude,currentPosition.longitude);if(!nearest)return;
 if(nearest.distance>ROUTE_OFFROAD_KM && Date.now()-lastRerouteAt>REROUTE_COOLDOWN_MS)rerouteLive();
}
async function rerouteLive(){
 if(!currentPosition||!toLocation||!activeRoute||rerouteBusy)return;rerouteBusy=true;lastRerouteAt=Date.now();lastNavReroute={...currentPosition};
 try{const r=await fetch(API.route,{method:"POST",headers:{"Content-Type":"application/json","X-CSRFToken":csrfToken()},body:JSON.stringify({from:currentPosition,to:toLocation,mode})}).then(x=>x.json());if(r.success){window.lastRoutes=r.routes||[r.route];activeRoute=r.route||r.routes[0];navStepIndex=0;lastSpokenStep=-1;routeLayers.forEach(x=>map.removeLayer(x));routeLayers=[];drawRoutes(window.lastRoutes);showSteps(activeRoute);document.getElementById("awarenessText").textContent="Route updated for your new road."}}
 catch(e){}finally{rerouteBusy=false}
}
function startNavigation(){
 if(!currentPosition){locateMe(true);setTimeout(()=>startNavigation(),1500);return}if(!activeRoute){alert("Find a route first.");return}
 document.getElementById("navHud").classList.remove("hidden");lastNavReroute={...currentPosition};lastRerouteAt=Date.now();navStepIndex=0;lastSpokenStep=-1;document.getElementById("navDestination").textContent=toLocation?.name||"Destination";document.getElementById("routePanel").classList.add("hidden");
 updateNavHUD();if(!watchId)locateMe();if(navTimer)clearInterval(navTimer);navTimer=setInterval(()=>{updateNavHUD();speakNextManeuver()},2000);speakNextManeuver();
>>>>>>> 18b97f5c09e78b2c0578622a3fd9d3bbb52bf3b5
}
function stopNavigation(){document.getElementById("navHud").classList.add("hidden");if(navTimer)clearInterval(navTimer);navTimer=null;speechStop();if(navLine){map.removeLayer(navLine);navLine=null}}
function recenterNavigation(){if(currentPosition)map.setView([currentPosition.latitude,currentPosition.longitude],17,{animate:true})}
function updateNavHUD(){
<<<<<<< HEAD
 if(!currentPosition||!toLocation||!activeRoute)return;const nearest=nearestPointOnRoute(activeRoute,currentPosition.latitude,currentPosition.longitude);const d=remainingRouteDistanceKm(activeRoute,currentPosition.latitude,currentPosition.longitude);
 document.getElementById("navRemaining").textContent=d<1?(d*1000).toFixed(0)+" m":d.toFixed(1)+" km";
 if(d<=0.035){document.getElementById("navInstruction").textContent="You have arrived at your destination.";document.getElementById("awarenessText").textContent="Arrived. Navigation can be stopped now.";speechStop();}
 const speed=currentPosition.speed?currentPosition.speed*3.6:0;document.getElementById("navSpeed").textContent=speed.toFixed(0);
 const mins=activeRoute.duration_minutes*(d/Math.max(activeRoute.distance_km,.1));document.getElementById("navEta").textContent=new Date(Date.now()+mins*60000).toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"});
 if(navLine)map.removeLayer(navLine);const geom=remainingRouteGeometry(activeRoute,currentPosition.latitude,currentPosition.longitude);navLine=L.geoJSON(geom,{style:{color:"#2563eb",weight:2.2,opacity:.82,lineCap:"round",lineJoin:"round"}}).addTo(map);
 if(document.getElementById("navHud")&&!document.getElementById("navHud").classList.contains("hidden")){const z=map.getZoom();if(z>=15)map.panTo([currentPosition.latitude,currentPosition.longitude],{animate:true,duration:.22})}
=======
 if(!currentPosition||!toLocation||!activeRoute)return;const nearest=nearestPointOnRoute(activeRoute,currentPosition.latitude,currentPosition.longitude);const d=nearest?.distance<0.12?_haversine(currentPosition.latitude,currentPosition.longitude,toLocation.latitude,toLocation.longitude):_haversine(currentPosition.latitude,currentPosition.longitude,toLocation.latitude,toLocation.longitude);
 document.getElementById("navRemaining").textContent=d<1?(d*1000).toFixed(0)+" m":d.toFixed(1)+" km";const speed=currentPosition.speed?currentPosition.speed*3.6:0;document.getElementById("navSpeed").textContent=speed.toFixed(0);const mins=activeRoute.duration_minutes*(d/Math.max(activeRoute.distance_km,.1));document.getElementById("navEta").textContent=new Date(Date.now()+mins*60000).toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"});
 if(navLine)map.removeLayer(navLine);const geom=remainingRouteGeometry(activeRoute,currentPosition.latitude,currentPosition.longitude);navLine=L.geoJSON(geom,{style:{color:"#2563eb",weight:3,opacity:.82,lineCap:"round",lineJoin:"round"}}).addTo(map);
 if(document.getElementById("navHud")&&!document.getElementById("navHud").classList.contains("hidden")){const z=map.getZoom();if(z>=15)map.panTo([currentPosition.latitude,currentPosition.longitude],{animate:true,duration:.35})}
>>>>>>> 18b97f5c09e78b2c0578622a3fd9d3bbb52bf3b5
}
function speakNextManeuver(){
 if(!currentPosition||!activeRoute?.steps?.length)return;let best=navStepIndex,bestD=Infinity;for(let i=Math.max(0,navStepIndex-1);i<activeRoute.steps.length;i++){const s=activeRoute.steps[i],loc=s.location||[];if(loc.length<2)continue;const d=_haversine(currentPosition.latitude,currentPosition.longitude,loc[0],loc[1]);if(d<bestD){bestD=d;best=i}}navStepIndex=best;const step=activeRoute.steps[best];
 document.getElementById("navInstruction").textContent=step?`${step.instruction}${bestD<1?` · ${bestD<1?(bestD*1000).toFixed(0)+" m":bestD.toFixed(1)+" km"} ahead`:""}`:"Follow the highlighted road.";
 if(step&&bestD<0.12&&best!==lastSpokenStep){lastSpokenStep=best;speakText(step.instruction)}
 if(step)document.getElementById("awarenessText").textContent=bestD<1?`${step.instruction} · ${(bestD*1000).toFixed(0)} m ahead`:`Next: ${step.instruction}`;
}
function _haversine(a,b,c,d){const R=6371,p=Math.PI/180,x=(c-a)*p,y=(d-b)*p;return 2*R*Math.asin(Math.sqrt(Math.sin(x/2)**2+Math.cos(a*p)*Math.cos(c*p)*Math.sin(y/2)**2))}

async function loadNearby(type){if(!currentPosition){locateMe();alert("Allow location first, then choose Nearby.");return}const box=document.getElementById("nearbyResults");box.innerHTML="<p class='muted'>Finding nearby options…</p>";togglePanel("nearbyPanel");try{const d=await fetch(apiUrl(API.nearby,{lat:currentPosition.latitude,lon:currentPosition.longitude,type,radius:12000})).then(r=>r.json());box.innerHTML=(d.results||[]).map(x=>{const safeName=JSON.stringify(String(x.name||"Place")).replace(/</g,"\\u003c").replace(/>/g,"\\u003e");return `<div class="result-card"><b>${escapeHtml(x.name)}</b><small>${escapeHtml(x.category||type)} · ${x.distance_m<1000?x.distance_m+" m":(x.distance_m/1000).toFixed(1)+" km"} · ${escapeHtml(x.source||"OpenStreetMap")}</small><button onclick='setDestination(${Number(x.latitude)},${Number(x.longitude)},${safeName})'>Directions</button></div>`}).join("")||"<p class='muted'>No nearby results found in this NCR radius.</p>"}catch(e){box.innerHTML="<p class='muted'>Nearby service is temporarily unavailable.</p>"}}
function setDestination(lat,lon,name){toLocation={latitude:lat,longitude:lon,name};document.getElementById("toInput").value=name;closePanel("nearbyPanel");findRoute()}

async function fetchWeather(lat,lon){const requestId=++weatherRequestSerial;try{const d=await fetch(apiUrl(API.weather,{lat,lon})).then(r=>r.json());if(requestId!==weatherRequestSerial||d.error)return;renderWeather(d,"Your current location")}catch(e){}}
async function fetchDestinationWeather(){if(!toLocation)return;const requestId=++weatherRequestSerial;try{const d=await fetch(apiUrl(API.weather,{lat:toLocation.latitude,lon:toLocation.longitude})).then(r=>r.json());if(requestId!==weatherRequestSerial||d.error)return;renderWeather(d,toLocation.name||"Destination");const c=d.current||{},rain=d.daily?.precipitation_probability_max?.[0]??0;document.getElementById("destinationWeatherText").textContent=`${toLocation.name||"Destination"}: ${Math.round(c.temperature_2m??0)}° · ${weatherText(c.weather_code)} · feels ${Math.round(c.apparent_temperature??c.temperature_2m??0)}° · rain ${rain}% today.`}catch(e){}}
function renderWeather(d,place){const c=d.current||{},rain=d.daily?.precipitation_probability_max?.[0]??0;document.getElementById("weatherTemp").textContent=Math.round(c.temperature_2m??0)+"°";document.getElementById("weatherText").textContent=weatherText(c.weather_code);document.getElementById("weatherFeels").textContent=Math.round(c.apparent_temperature??c.temperature_2m??0)+"°";document.getElementById("weatherRain").textContent=rain+"%";document.getElementById("weatherWind").textContent=Math.round(c.wind_speed_10m??0)+" km/h";document.getElementById("weatherIcon").textContent=weatherEmoji(c.weather_code);document.getElementById("weatherPlace").textContent=place;renderForecast(d.daily);renderTips(c)}
function weatherText(c){if(c===0)return"Clear sky";if([1,2,3].includes(c))return"Partly cloudy";if([45,48].includes(c))return"Hazy / foggy";if([51,53,55,61,63,65,80,81,82].includes(c))return"Rain likely";if([95,96,99].includes(c))return"Thunderstorm";return"Mixed conditions"}
function renderForecast(d){if(!d?.time)return;document.getElementById("forecast").innerHTML=d.time.map((x,i)=>{const code=d.weather_code?.[i]??0,rain=d.precipitation_probability_max?.[i]??0,wind=d.wind_speed_10m_max?.[i];return `<div class="day"><b>${new Date(x).toLocaleDateString([], {weekday:"short"})}</b><span>${weatherEmoji(code)}</span><small>${Math.round(d.temperature_2m_max?.[i]??0)}° / ${Math.round(d.temperature_2m_min?.[i]??0)}°</small><small>Rain ${rain}%${Number.isFinite(wind)?` · ${Math.round(wind)} km/h`:""}</small></div>`}).join("")}
function weatherEmoji(c){return c===0?"☀️":[1,2,3].includes(c)?"⛅":[45,48].includes(c)?"🌫️":[51,53,55,61,63,65,80,81,82].includes(c)?"🌧️":[95,96,99].includes(c)?"⛈️":"🌤️"}
function renderTips(c){const t=[];if(c.precipitation>0||c.weather_code>=51)t.push("Rain-aware: allow extra travel time and watch for slippery roads.");if(c.wind_speed_10m>30)t.push("Wind is elevated: take extra care on two-wheelers.");t.push(mode==="foot"?"Walking: use crossings and sidewalks where available.":mode==="bike"?"Bike: stay visible and keep both hands available for control.":"Drive safely and use voice guidance instead of looking at the screen.");document.getElementById("weatherTips").innerHTML=t.map(x=>`<div class="tip">✦ ${x}</div>`).join("")}
function toggleWeather(){togglePanel("weatherPanel");if(currentPosition)fetchWeather(currentPosition.latitude,currentPosition.longitude);else locateMe();if(toLocation)fetchDestinationWeather()}
async function fetchAwareness(){try{const d=await fetch(apiUrl(API.awareness,{mode})).then(r=>r.json());document.getElementById("awarenessText").textContent=d.tips?.[0]||"Stay aware while travelling."}catch(e){}}
async function loadTrainSchedule(){try{const d=await fetch(API.train).then(r=>r.json());document.getElementById("trainSchedule").innerHTML=(d.slots||[]).map(s=>`<div class="slot"><b>${s.label}</b><span>${s.time}</span><small>${s.note}</small></div>`).join("")}catch(e){}}

/* Voice control — one colorful bottom button that can always be stopped. */
function speakText(text){if(!("speechSynthesis" in window))return;speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(text);u.rate=.95;u.pitch=1;u.volume=1;u.onstart=()=>setListenState(true);u.onend=()=>setListenState(false);u.onerror=()=>setListenState(false);speechSynthesis.speak(u)}
function speechStop(){if("speechSynthesis" in window)speechSynthesis.cancel();setListenState(false)}
function toggleSpeech(){if("speechSynthesis" in window&&speechSynthesis.speaking){speechStop();return}const place=document.getElementById("weatherPlace")?.innerText||"your location",temp=document.getElementById("weatherTemp")?.innerText||"",summary=document.getElementById("weatherText")?.innerText||"",days=[...document.querySelectorAll("#forecast .day")].map(x=>x.innerText.replace(/\n/g," ")).join(". "),dest=document.getElementById("destinationWeatherText")?.innerText||"";speakText(`GoPlan weather for ${place}. It is ${temp}, ${summary}. ${dest}. Seven day forecast: ${days}`)}
function setListenState(active){const b=document.getElementById("listenBtn"),t=document.getElementById("listenText");if(!b)return;b.classList.toggle("speaking",active);t.textContent=active?"Stop":"Listen";b.querySelector("span").textContent=active?"■":"🔊"}

locateMe(false);loadTrainSchedule();setTimeout(()=>map.invalidateSize(),400);
