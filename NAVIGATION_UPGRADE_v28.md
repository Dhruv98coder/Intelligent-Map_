# GoPlan IntelligentMap v28 — Smart Navigation Upgrade

## Navigation behavior
- Remaining distance is calculated along the routed road geometry instead of straight-line distance.
- Blue navigation line shows only the remaining road and is thinner during live navigation.
- GPS off-route threshold reduced to ~35 m.
- Reroute cooldown reduced to ~2.8 s with a small movement guard to avoid repeated reroute spam.
- Reroute starts from the user's live position and replaces the active road route.
- Navigation refreshes every second while active.
- Arrival is detected at approximately 35 m from the routed destination.

## Existing v27 features retained
- Dekho Bharat tricolor branding.
- Intelligent Map · Delhi NCR subtitle.
- Search show/hide toggle.
- Delhi NCR From/To search.
- Metro planner and modern Metro branding.
- Weather panel and listen/stop voice control.
- Smart Connect Auto → Bus → Walk estimate.

## Important data note
The bus leg remains an estimated planning suggestion because this package does not contain a verified live Delhi NCR bus timetable/GTFS feed. The UI labels those values as estimates rather than live departures.
