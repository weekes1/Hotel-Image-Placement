ROOM_SUBJECTS = {"guest_room", "suite"}

DINING_SUBJECTS = {"restaurant", "bar", "food", "drinks"}

AMENITY_SUBJECTS = {
    "spa", "gym", "pool", "pool_indoor",
    "treatment_room", "garden", "kids_facility",
}

HERO_SUBJECTS = {"exterior", "entrance", "grounds"}

# def build_presentation(images, audience):

    # if audience == 'member':


    # if audience == "curator":
    #     continue


def filter_usable_images(images):
    """Return only images explicitly marked as usable."""
    return [
        image
        for image in images
        if image.get("usable") is True
    ]