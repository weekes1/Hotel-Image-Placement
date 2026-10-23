ROOM_SUBJECTS = {"guest_room", "suite"}

DINING_SUBJECTS = {"restaurant", "bar", "food", "drinks"}

AMENITY_SUBJECTS = {
    "spa", "gym", "pool", "pool_indoor",
    "treatment_room", "garden", "kids_facility",
}

HERO_SUBJECTS = {"exterior", "entrance", "grounds"}

def build_presentation(images, audience):

    # if audience == 'member':

    #     return select_member_images(images)

    if audience == "curator":
        select_curator_images(images)

    raise ValueError(f"Unsupported audience: {audience}")


def filter_usable_images(images):
    """Return only images explicitly marked as usable."""
    return [
        image
        for image in images
        if image.get("usable") is True
    ]



def image_strength(image):
    quality = image.get("quality_score")
    appeal = image.get("appeal_score")

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