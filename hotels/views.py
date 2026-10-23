from django.shortcuts import render

import logging

from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .repository import HotelDataError, HotelNotFound, get_hotel

from .selection import filter_usable_images

from .selection import build_presentation

logger = logging.getLogger(__name__)


@require_GET
def image_presentation(request, hotel_id):
    audience = request.GET.get("audience")

    if audience not in ("curator", "member"):
        return JsonResponse(
            {"error": "audience must be one of the shown options"},
            status=400,
        )

    try:
        hotel = get_hotel(hotel_id)
    except HotelNotFound:
        return JsonResponse(
            {"error": "Hotel not found."},
            status=404,
        )
    except HotelDataError:
        logger.exception("Failed to load hotel metadata")
        return JsonResponse(
            {"error": "Hotel data is currently unavailable."},
            status=500,
        )

    images = build_presentation(hotel["images"], audience)

    return JsonResponse(
        {
            "hotel_id": hotel["id"],
            "hotel_name": hotel["name"],
            "audience": audience,
            "images": images,
        }
    )
