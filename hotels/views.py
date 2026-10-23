import logging
from pathlib import Path

from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET

from .repository import DATA_DIR, HotelDataError, HotelNotFound, get_hotel, list_hotels
from .selection import build_presentation

logger = logging.getLogger(__name__)


def _preview_image(image, hotel_id):
    """Add display fields without changing the selected image metadata."""
    file = image.get("file")
    url = ""
    if isinstance(file, str) and file.startswith("images/"):
        url = reverse(
            "hotel-image",
            kwargs={"hotel_id": hotel_id, "filename": Path(file).name},
        )

    subjects = image.get("subjects")
    labels = (
        [subject.replace("_", " ") for subject in subjects if isinstance(subject, str)]
        if isinstance(subjects, list) else []
    )
    return {
        **image,
        "url": url,
        "label": ", ".join(labels) or "Hotel image",
    }


@require_GET
def showcase(request):
    context = {"hotels": [], "audience": request.GET.get("audience", "member")}
    status = 200

    try:
        context["hotels"] = sorted(list_hotels(), key=lambda hotel: hotel["name"].casefold())
        hotel_id = request.GET.get("hotel_id", context["hotels"][0]["id"])
        context["selected_hotel_id"] = hotel_id

        if context["audience"] not in ("curator", "member"):
            context["error"] = "Choose either the curator or member audience."
            status = 400
        else:
            hotel = get_hotel(hotel_id)
            presentation = build_presentation(hotel["images"], context["audience"])
            preview = lambda image: _preview_image(image, hotel_id)
            context["hotel"] = hotel
            context["api_url"] = (
                reverse("image-presentation", kwargs={"hotel_id": hotel_id})
                + "?audience=" + context["audience"]
            )

            if context["audience"] == "member":
                context["hero"] = preview(presentation["hero"]) if presentation["hero"] else None
                context["galleries"] = [
                    {"name": "Amenities", "images": [preview(image) for image in presentation["amenities"]]},
                    {"name": "Dining", "images": [preview(image) for image in presentation["dining"]]},
                ]
            else:
                context["galleries"] = [
                    {"name": "Curator gallery", "images": [preview(image) for image in presentation["gallery"]]},
                ]
    except HotelNotFound:
        context["error"] = "That hotel was not found. Choose another hotel above."
        status = 404
    except HotelDataError:
        logger.exception("Failed to load showcase metadata")
        context["error"] = "Hotel data is currently unavailable."
        status = 500

    return render(request, "hotels/showcase.html", context, status=status)


@require_GET
def hotel_image(request, hotel_id, filename):
    """Serve only image files listed in the selected hotel's metadata."""
    try:
        hotel = get_hotel(hotel_id)
    except (HotelNotFound, HotelDataError):
        raise Http404("Image not found") from None

    if not any(image.get("file") == f"images/{filename}" for image in hotel["images"]):
        raise Http404("Image not found")

    path = (DATA_DIR / hotel_id / "images" / filename).resolve()
    if not path.is_relative_to(DATA_DIR.resolve()):
        raise Http404("Image not found")

    try:
        return FileResponse(path.open("rb"))
    except OSError:
        raise Http404("Image not found") from None


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

    presentations = build_presentation(hotel["images"], audience)

    return JsonResponse(
        {
            "hotel_id": hotel["id"],
            "hotel_name": hotel["name"],
            "audience": audience,
            "presentations": presentations,
        }
    )
