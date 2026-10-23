import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from .repository import HotelDataError, HotelNotFound, get_hotel, list_hotels
from .selection import filter_usable_images
from .selection import filter_usable_images, select_curator_images

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