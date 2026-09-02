from .data_loader import load_metro_map_data


def search_station(query, limit=10):
    """
    Search metro stations by name.
    """

    query = str(query or "").strip().lower()

    if len(query) < 2:
        return []

    try:
        df = load_metro_map_data()
    except FileNotFoundError:
        return []

    # Find the station-name column
    possible_columns = [
        "station_name",
        "station",
        "name",
        "Station Name",
        "Station"
    ]

    station_column = None

    for column in possible_columns:
        if column in df.columns:
            station_column = column
            break

    if station_column is None:
        raise ValueError(
            "Station name column not found in metro dataset."
        )

    matches = df[
        df[station_column]
        .astype(str)
        .str.lower()
        .str.contains(query, na=False)
    ]

    return matches.head(limit).to_dict("records")