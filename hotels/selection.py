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


def image_identity(image):
    """Use a valid ID, falling back to the file path within this hotel."""
    for field in ("id", "file"):
        value = image.get(field)
        if isinstance(value, str) and value.strip():
            return (field, value)

    return None


def _member_sort_key(image):
    source_order = image.get("sort_order")

    if isinstance(source_order, bool) or not isinstance(source_order, int):
        source_order = float("inf")

    return (
        -image_strength(image),
        source_order,
        image_identity(image) or ("", ""),
    )

MEMBER_GALLERY_LIMIT = 5


def _select_member_gallery(ranked_images, subjects, used_keys):
    gallery = []

    for image in ranked_images:
        key = image_identity(image)
        if key in used_keys:
            continue

        if not image_subjects(image) & subjects:
            continue

        gallery.append(image)
        used_keys.add(key)

        if len(gallery) >= MEMBER_GALLERY_LIMIT:
            break

    return gallery

def select_member_images(images):
    usable_images = filter_usable_images(images)

    candidates = [
        image
        for image in usable_images
        if image_identity(image) is not None
    ]

    ranked_images = sorted(candidates, key=_member_sort_key)

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

    used_keys = set()

    if hero is not None:
        used_keys.add(image_identity(hero))

    # Fill the category with fewer available candidates first.
    categories = [
        ("amenities", AMENITY_SUBJECTS),
        ("dining", DINING_SUBJECTS),
    ]

    categories.sort(
        key=lambda category: sum(
            image_identity(image) not in used_keys
            and bool(image_subjects(image) & category[1])
            for image in ranked_images
        )
    )

    galleries = {}

    for name, subjects in categories:
        galleries[name] = _select_member_gallery(
            ranked_images,
            subjects,
            used_keys,
        )

    return {
        "hero": hero,
        "amenities": galleries["amenities"],
        "dining": galleries["dining"],
    }
