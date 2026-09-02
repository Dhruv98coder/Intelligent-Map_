# GoPlan Delhi NCR Road Map Upgrade

## What this fixes
- Road mode is independent of the metro map.
- General Delhi/NCR place search is now primary; metro stations are secondary search results.
- Search indexes place name, aliases, address, category, location, and destination query fields from the curated dataset.
- Explicit Enter/search uses bounded OSM/Nominatim fallback. Public Nominatim is not used for autocomplete.
- Nearby supports food, hotels, hospitals/clinics, pharmacy, ATM, banks, fuel, parking, schools, shopping, police, toilets, EV charging, bus stops and tourist places.
- Car, bike and walking profiles request alternative road routes, route geometry, and turn-by-turn steps.
- Live navigation updates the position, ETA, distance, next instruction, voice instruction and reroutes after meaningful off-route deviation.
- NCR coordinate fence prevents road search/routing from leaving the configured Delhi NCR area.

## Production map stack
OSRM route service supports alternatives, steps and GeoJSON geometry. Public OSRM instances are suitable for prototypes; use a dedicated routing server/provider for production volume.

OpenStreetMap standard tiles are used only as an interactive base map. Production deployments should review OSM tile usage requirements and use an OSM-derived hosted/self-hosted tile provider when traffic grows.

Nominatim's public policy forbids client-side autocomplete and systematic POI harvesting; this project therefore uses local/curated search for typing and explicit remote search only after submit.

## Road modes
- Car: OSRM driving profile
- Bike: configurable routed-bike endpoint
- Walk: configurable routed-foot endpoint

No metro logic is used by the road routing endpoint. Metro remains a separate application/map surface.

## Road-map behavior fix (latest)
- Road search is independent of the metro station index.
- Metro results appear on road search only for explicit queries containing metro/station/DMRC; the dedicated Metro Map remains a separate mode.
- The curated GoPlan Delhi/NCR Places dataset (81 place records) is loaded as a TSV and indexed by place name, aliases, address, category and destination query fields.
- Press **Search** or Enter to perform an explicit wider NCR geocoding lookup through Nominatim; this is not used as keystroke autocomplete.
- Current GPS position can be reverse-geocoded to a human-readable NCR address.
- Car, Bike and Walk use independent road-routing profiles and show route alternatives, distance, ETA and turn-by-turn steps.
- Start Navigation uses live GPS, off-route detection and rerouting from the current location.
