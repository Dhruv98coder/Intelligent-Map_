# GoPlan IntelligentMap — Delhi NCR

Professional travel map for Delhi NCR.

## Core maps
1. Road map: Car, Bike and Walk with alternative road routes, distance, ETA and turn-by-turn instructions.
2. Metro map: a separate full Delhi NCR Metro network view with line colors, station search, interchanges and station-by-station guidance.
3. Live navigation: browser GPS tracking, navigation HUD and automatic route refresh when the tracked position changes significantly.

## Smart travel
- From / To search restricted to Delhi NCR.
- Nearby Metro, Railway, Food, Hotels, Hospitals, Pharmacy, ATMs and tourist places.
- GoPlan's curated Delhi places dataset is used first for tourist results and search.
- Current weather + destination weather + seven-day forecast.
- Context-aware awareness tips.
- Rail planning windows are intentionally labelled as planning windows, not live railway departures.

## Data / services
- OpenStreetMap tiles
- Nominatim for Delhi NCR place search
- OSRM for road and walking routes
- Overpass / OpenStreetMap for nearby POIs
- Open-Meteo for current and seven-day weather
- User-supplied Delhi Metro CSV datasets for the metro model

## Run
```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open http://127.0.0.1:8000/

The application is intentionally bounded to Delhi NCR.
