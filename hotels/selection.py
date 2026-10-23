from math import isfinite

ROOM_SUBJECTS = {"guest_room", "suite"}

DINING_SUBJECTS = {"restaurant", "bar", "food", "drinks"}

AMENITY_SUBJECTS = {
    "spa", "gym", "pool", "pool_indoor",
    "treatment_room", "garden", "kids_facility",
}

HERO_SUBJECTS = {"exterior", "entrance", "grounds"}

def build_presentation(images, audience):

    if audience == 'curator':

        return {
            "gallery": select_curator_images(images),
        }

    if audience == "member":
        return select_member_images(images)

    raise ValueError(f"Unsupported audience: {audience}")


def filter_usable_images(images):
    """Return only images explicitly marked as usable."""
    return [
        image
        for image in images
        if image.get("usable") is True
    ]

def _score_guard(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0.0

    if not isfinite(value):
        return 0.0

    return max(0.0, min(1.0, value))

def image_strength(image):
    quality = _score_guard(image.get("quality_score"))
    appeal = _score_guard(image.get("appeal_score"))

    return 0.5 * quality + 0.5 * appeal

def _curator_sort_key(image):
    subjects = image.get("subjects")

    if not isinstance(subjects, list):
        subjects = []

    preferred_subjects = ROOM_SUBJECTS | DINING_SUBJECTS

    is_preferred = any(
        subject in preferred_subjects
        for subject in subjects
        if isinstance(subject, str)
    )

    group = 0 if is_preferred else 1

    source_order = image.get("sort_order")

    if isinstance(source_order, bool) or not isinstance(source_order, int):
        source_order = float("inf")

    return (
        group,
        -image_strength(image),
        source_order,
        str(image.get("id", "")),
    )


def select_curator_images(images):
    usable_images = filter_usable_images(images)

    return sorted(usable_images, key=_curator_sort_key)

def image_subjects(image):
    subjects = image.get("subjects")

    if not isinstance(subjects, list):
        return set()

    return {
        subject
        for subject in subjects
        if isinstance(subject, str)
    }


def _member_sort_key(image):
    source_order = image.get("sort_order")

    if isinstance(source_order, bool) or not isinstance(source_order, int):
        source_order = float("inf")

    return (
        -image_strength(image),
        source_order,
        str(image.get("id", "")),
    )

MEMBER_GALLERY_LIMIT = 5


def _select_member_gallery(ranked_images, subjects, used_ids):
    gallery = []

    for image in ranked_images:
        if image["id"] in used_ids:
            continue

        if not image_subjects(image) & subjects:
            continue

        gallery.append(image)
        used_ids.add(image["id"])

        if len(gallery) >= MEMBER_GALLERY_LIMIT:
            break

    return gallery

def select_member_images(images):
    usable_images = filter_usable_images(images)

    ranked_images = sorted(usable_images, key=_member_sort_key)

    # Prefer explicit building/property subjects.
    hero_candidates = [
        image
        for image in ranked_images
        if image_subjects(image) & HERO_SUBJECTS
    ]

    # Otherwise, look for a broader sense of place.
    if not hero_candidates:
        fallback_subjects = {
            "lobby", "garden", "terrace", "view", "lounge",
        }

        hero_candidates = [
            image
            for image in ranked_images
            if image_subjects(image) & fallback_subjects
        ]

    # Last resort: use the strongest remaining usable image.
    if not hero_candidates:
        hero_candidates = ranked_images

    hero = hero_candidates[0] if hero_candidates else None

    used_ids = set()

    if hero is not None:
        used_ids.add(hero["id"])

    # Fill the category with fewer available candidates first.
    categories = [
        ("amenities", AMENITY_SUBJECTS),
        ("dining", DINING_SUBJECTS),
    ]

    categories.sort(
        key=lambda category: sum(
            image["id"] not in used_ids
            and bool(image_subjects(image) & category[1])
            for image in ranked_images
        )
    )

    galleries = {}

    for name, subjects in categories:
        galleries[name] = _select_member_gallery(
            ranked_images,
            subjects,
            used_ids,
        )

    return {
        "hero": hero,
        "amenities": galleries["amenities"],
        "dining": galleries["dining"],
    }