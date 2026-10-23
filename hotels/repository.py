"""Read hotel metadata from the supplied dataset, independently of Django."""

import json
from pathlib import Path


DATA_DIR = (
    Path(__file__).resolve().parent.parent / "data" / "paris-hotels-image-placement"
)


class HotelNotFound(LookupError):
    """The requested hotel ID is not in the dataset."""


class HotelDataError(RuntimeError):
    """The dataset is missing or contains invalid hotel metadata."""


def _load_hotels():
    """Discover hotel files and index their contents by metadata ID."""
    paths = sorted(DATA_DIR.glob("*/hotel.json"))
    if not paths:
        raise HotelDataError(f"No hotel.json files found in {DATA_DIR}")

    hotels = {}
    for path in paths:
        try:
            hotel = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise HotelDataError(f"Could not read hotel metadata: {path}") from exc

        if not isinstance(hotel, dict):
            raise HotelDataError(f"Expected a JSON object in {path}")

        hotel_id = hotel.get("id")
        if not isinstance(hotel_id, str) or not hotel_id.strip():
            raise HotelDataError(f"Missing or invalid hotel ID in {path}")
        if hotel_id in hotels:
            raise HotelDataError(f"Duplicate hotel ID: {hotel_id}")

        name = hotel.get("name")
        hotel["name"] = name 
        hotel.setdefault("images", [])
        if not isinstance(hotel["images"], list):
            raise HotelDataError(f"Expected an images list in {path}")

        hotels[hotel_id] = hotel

    return hotels


def list_hotels():
    """Return hotel IDs and names in a stable order."""
    hotels = _load_hotels()
    return [
        {"id": hotel_id, "name": hotels[hotel_id]["name"]}
        for hotel_id in sorted(hotels)
    ]


def get_hotel(hotel_id):
    """Return a hotel's metadata, or raise HotelNotFound."""
    hotels = _load_hotels()
    try:
        return hotels[hotel_id]
    except KeyError:
        raise HotelNotFound(f"Unknown hotel: {hotel_id}") from None

