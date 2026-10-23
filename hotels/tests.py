import json
from copy import deepcopy
from itertools import permutations
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from .repository import HotelDataError, HotelNotFound, get_hotel, list_hotels
from .selection import filter_usable_images
from .selection import filter_usable_images, select_curator_images, select_member_images


class VarietySelectionTests(TestCase):
    def image(self, image_id, strength, *subjects):
        return {
            "id": image_id,
            "usable": True,
            "subjects": list(subjects),
            "quality_score": strength,
            "appeal_score": strength,
        }

    def test_curator_promotes_close_dining_image_but_preserves_group_priority(self):
        images = [
            self.image("room-1", 0.95, "guest_room"),
            self.image("room-2", 0.94, "suite"),
            self.image("restaurant", 0.92, "restaurant"),
            self.image("exterior", 1.0, "exterior"),
        ]

        result = select_curator_images(images)

        self.assertEqual(
            [image["id"] for image in result],
            ["room-1", "restaurant", "room-2", "exterior"],
        )

    def test_variety_never_promotes_an_image_outside_the_score_margin(self):
        for dining_score, expected in (
            (0.89, ["room-1", "restaurant", "room-2"]),
            (0.889, ["room-1", "room-2", "restaurant"]),
        ):
            with self.subTest(dining_score=dining_score):
                images = [
                    self.image("room-1", 0.95, "guest_room"),
                    self.image("room-2", 0.94, "suite"),
                    self.image("restaurant", dining_score, "restaurant"),
                ]

                self.assertEqual(
                    [image["id"] for image in select_curator_images(images)],
                    expected,
                )

    def test_member_amenities_treat_pool_labels_as_one_family(self):
        images = [
            self.image("hero", 1.0, "exterior"),
            self.image("pool-1", 0.95, "pool"),
            self.image("pool-2", 0.94, "pool_indoor"),
            self.image("spa", 0.92, "spa"),
            self.image("gym", 0.70, "gym"),
        ]

        result = select_member_images(images)

        self.assertEqual(result["hero"]["id"], "hero")
        self.assertEqual(
            [image["id"] for image in result["amenities"]],
            ["pool-1", "spa", "pool-2", "gym"],
        )

    def test_member_dining_diversifies_spaces_food_and_drinks(self):
        images = [
            self.image("hero", 1.0, "exterior"),
            self.image("restaurant-1", 0.95, "restaurant"),
            self.image("restaurant-2", 0.94, "restaurant"),
            self.image("food", 0.92, "food"),
            self.image("drinks", 0.91, "drinks"),
        ]

        result = select_member_images(images)

        self.assertEqual(
            [image["id"] for image in result["dining"]],
            ["restaurant-1", "food", "drinks", "restaurant-2"],
        )

    def test_variety_considers_candidates_before_applying_gallery_limit(self):
        images = [self.image("hero", 1.0, "exterior")]
        images += [
            self.image(f"pool-{index}", score, "pool")
            for index, score in enumerate((0.95, 0.94, 0.93, 0.92, 0.91))
        ]
        images.append(self.image("spa", 0.90, "spa"))

        result = select_member_images(images)

        self.assertEqual(
            [image["id"] for image in result["amenities"]],
            ["pool-0", "spa", "pool-1", "pool-2", "pool-3"],
        )

    def test_multisubject_images_mark_every_matching_family_as_seen(self):
        images = [
            self.image("room-and-food", 0.95, "guest_room", "food"),
            self.image("room", 0.94, "suite"),
            self.image("food", 0.93, "food"),
            self.image("restaurant", 0.92, "restaurant"),
        ]

        self.assertEqual(
            [image["id"] for image in select_curator_images(images)],
            ["room-and-food", "restaurant", "room", "food"],
        )

    def test_incidental_and_out_of_category_tags_do_not_create_variety(self):
        images = [
            self.image("hero", 1.0, "exterior"),
            self.image("pool-1", 0.95, "pool"),
            self.image("pool-2", 0.94, "pool"),
            self.image("pool-3", 0.92, "pool", "ambiance", "people", "guest_room"),
        ]

        self.assertEqual(
            [image["id"] for image in select_member_images(images)["amenities"]],
            ["pool-1", "pool-2", "pool-3"],
        )

    def test_order_is_deterministic_without_modifying_input(self):
        images = [
            self.image("room", 0.95, "guest_room"),
            self.image("restaurant-b", 0.92, "restaurant"),
            self.image("restaurant-a", 0.92, "restaurant"),
            self.image("food", 0.91, "food"),
        ]
        original = deepcopy(images)
        expected_curator = select_curator_images(images)
        expected_member = select_member_images(images)

        for ordering in permutations(images):
            self.assertEqual(select_curator_images(ordering), expected_curator)
            self.assertEqual(select_member_images(ordering), expected_member)

        self.assertEqual(images, original)


class ImageSelectionTests(TestCase):
    def test_keeps_only_usable_images_in_their_original_order(self):
        images = [
            {"id": "one", "usable": True},
            {"id": "two", "usable": False},
            {"id": "three"},
            {"id": "four", "usable": None},
            {"id": "five", "usable": True},
        ]

        result = filter_usable_images(images)

        self.assertEqual(result, [images[0], images[4]])


class HotelRepositoryTests(TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.data_dir = Path(directory.name)
        patcher = patch("hotels.repository.DATA_DIR", self.data_dir)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write_hotel(self, folder, metadata):
        path = self.data_dir / folder / "hotel.json"
        path.parent.mkdir()
        path.write_text(json.dumps(metadata), encoding="utf-8")
        return path

    def test_discovers_all_hotels_by_metadata_id_in_stable_order(self):
        self.write_hotel("first-folder", {"id": "b", "name": "Hotel B"})
        self.write_hotel("second-folder", {"id": "a", "name": "Hotel A"})
        self.assertEqual(
            list_hotels(),
            [{"id": "a", "name": "Hotel A"}, {"id": "b", "name": "Hotel B"}],
        )
        self.assertEqual(get_hotel("a")["name"], "Hotel A")

    def test_preserves_image_metadata_and_defaults_missing_optional_fields(self):
        image = {"id": "image-1", "subjects": ["suite", "food"]}
        self.write_hotel("one", {"id": "a", "images": [image]})
        self.write_hotel("two", {"id": "b"})
        self.assertEqual(get_hotel("a")["images"], [image])
        self.assertEqual(get_hotel("b"), {"id": "b", "name": "b", "images": []})

    def test_unknown_ids_are_looked_up_without_using_them_as_paths(self):
        self.write_hotel("one", {"id": "a"})
        for hotel_id in ("missing", "../../outside"):
            with self.subTest(hotel_id=hotel_id), self.assertRaises(HotelNotFound):
                get_hotel(hotel_id)

    def test_corrupt_json_reports_a_data_error(self):
        path = self.write_hotel("one", {"id": "a"})
        path.write_text("{broken", encoding="utf-8")
        with self.assertRaises(HotelDataError):
            list_hotels()

    def test_duplicate_ids_are_rejected_instead_of_overwritten(self):
        self.write_hotel("one", {"id": "a"})
        self.write_hotel("two", {"id": "a"})
        with self.assertRaises(HotelDataError):
            list_hotels()

    def test_empty_dataset_reports_a_data_error(self):
        with self.assertRaises(HotelDataError):
            list_hotels()


class CuratorSelectionTests(TestCase):
    def test_rooms_and_dining_lead_and_unusable_images_are_excluded(self):
        images = [
            {
                "id": "exterior",
                "usable": True,
                "subjects": ["exterior"],
                "quality_score": 1.0,
                "appeal_score": 1.0,
            },
            {
                "id": "room",
                "usable": True,
                "subjects": ["ambiance", "guest_room"],
                "quality_score": 0.8,
                "appeal_score": 0.8,
            },
            {
                "id": "dining",
                "usable": True,
                "subjects": ["restaurant", "food"],
                "quality_score": 0.9,
                "appeal_score": 0.9,
            },
            {
                "id": "unusable",
                "usable": False,
                "subjects": ["suite"],
                "quality_score": 1.0,
                "appeal_score": 1.0,
            },
        ]

        result = select_curator_images(images)

        self.assertEqual(
            [image["id"] for image in result],
            ["dining", "room", "exterior"],
        )

    def test_ties_use_source_order_then_id(self):
        images = [
            {"id": "b", "usable": True, "sort_order": 2},
            {"id": "a", "usable": True, "sort_order": 2},
            {"id": "c", "usable": True, "sort_order": 1},
        ]

        result = select_curator_images(images)

        self.assertEqual(
            [image["id"] for image in result],
            ["c", "a", "b"],
        )

        self.assertEqual(result, select_curator_images(list(reversed(images))))

    def test_incomplete_metadata_is_handled(self):
        images = [
            {
                "id": "missing",
                "usable": True,
                "subjects": None,
                "quality_score": None,
                "sort_order": None,
            },
            {
                "id": "scored",
                "usable": True,
                "quality_score": 0.8,
                "appeal_score": 0.8,
            },
        ]

        result = select_curator_images(images)

        self.assertEqual(
            [image["id"] for image in result],
            ["scored", "missing"],
        )

class MemberSelectionTests(TestCase):
    def test_file_identity_prevents_hero_and_gallery_duplicates(self):
        hero = {
            "file": "images/building.jpg",
            "usable": True,
            "subjects": ["exterior", "spa", "restaurant"],
        }
        shared = {
            "file": "images/shared.jpg",
            "usable": True,
            "subjects": ["spa", "restaurant"],
        }

        result = select_member_images([hero, dict(hero), shared, dict(shared)])

        self.assertEqual(result["hero"], hero)
        galleries = result["amenities"] + result["dining"]
        self.assertEqual(galleries, [shared])
        self.assertNotIn("id", result["hero"])

    def test_invalid_ids_fall_back_to_file(self):
        for image_id in (None, "", "   ", 123):
            with self.subTest(image_id=image_id):
                image = {
                    "id": image_id,
                    "file": "images/building.jpg",
                    "usable": True,
                    "subjects": ["exterior"],
                }

                result = select_member_images([image])

                self.assertEqual(result["hero"], image)

    def test_skips_images_without_a_valid_id_or_file(self):
        images = [
            {"usable": True},
            {"id": None, "file": "   ", "usable": True},
            {"id": "", "file": 123, "usable": True},
        ]

        self.assertEqual(
            select_member_images(images),
            {"hero": None, "amenities": [], "dining": []},
        )

    def test_file_identity_breaks_score_ties_deterministically(self):
        images = [
            {"file": "images/b.jpg", "usable": True, "subjects": ["exterior"]},
            {"file": "images/a.jpg", "usable": True, "subjects": ["exterior"]},
        ]

        result = select_member_images(images)

        self.assertEqual(result["hero"]["file"], "images/a.jpg")
        self.assertEqual(result, select_member_images(list(reversed(images))))

    def test_id_takes_precedence_and_does_not_collide_with_file_identity(self):
        images = [
            {"id": "same", "file": "first.jpg", "usable": True, "subjects": ["exterior"]},
            {"id": "same", "file": "second.jpg", "usable": True, "subjects": ["spa"]},
            {"file": "same", "usable": True, "subjects": ["restaurant"]},
        ]

        result = select_member_images(images)

        self.assertEqual(result["hero"], images[0])
        self.assertEqual(result["amenities"], [])
        self.assertEqual(result["dining"], [images[2]])

    def test_selects_hero_and_galleries_without_repeating_images(self):
        images = [
            {
                "id": "building",
                "usable": True,
                "subjects": ["exterior"],
                "quality_score": 0.9,
                "appeal_score": 0.9,
            },
            {
                "id": "pool",
                "usable": True,
                "subjects": ["pool_indoor"],
                "quality_score": 0.8,
                "appeal_score": 0.8,
            },
            {
                "id": "restaurant",
                "usable": True,
                "subjects": ["restaurant", "food"],
                "quality_score": 0.9,
                "appeal_score": 0.9,
            },
            {
                "id": "shared",
                "usable": True,
                "subjects": ["spa", "bar"],
                "quality_score": 0.7,
                "appeal_score": 0.7,
            },
            {
                "id": "unusable",
                "usable": False,
                "subjects": ["exterior"],
                "quality_score": 1.0,
                "appeal_score": 1.0,
            },
        ]

        result = select_member_images(images)

        self.assertEqual(result["hero"]["id"], "building")
        self.assertIn("pool", [i["id"] for i in result["amenities"]])
        self.assertIn("restaurant", [i["id"] for i in result["dining"]])

        selected = (
            [result["hero"]]
            + result["amenities"]
            + result["dining"]
        )
        ids = [image["id"] for image in selected]

        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(ids.count("shared"), 1)
        self.assertNotIn("unusable", ids)
        self.assertEqual(result, select_member_images(list(reversed(images))))

    def test_falls_back_to_a_room_when_no_property_image_exists(self):
        room = {
            "id": "room",
            "usable": True,
            "subjects": ["guest_room"],
        }

        self.assertEqual(
            select_member_images([room]),
            {"hero": room, "amenities": [], "dining": []},
        )

    def test_handles_no_usable_images(self):
        self.assertEqual(
            select_member_images([{"id": "bad", "usable": False}]),
            {"hero": None, "amenities": [], "dining": []},
        )
