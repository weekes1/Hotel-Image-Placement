# Paris Hotels — Image Placement Dataset

23 Paris hotels, 536 images (capped at 25/hotel), each image evaluated for quality, appeal, subjects, and usability.

## Layout

```
paris-hotels-image-placement/
├── hotels.json                 # index of all hotels (id, name, address, image_count, folder)
├── <hotel-uuid>/
│   ├── hotel.json              # hotel data (name, address, description, ...) + per-image metadata
│   └── images/
│       └── <image-uuid>.jpg    # filename == the image "id" in hotel.json
└── ... (one folder per hotel)
```

## hotel.json

Top-level: `id`, `name`, `address`, `location`, `city`, `country`, `latitude`, `longitude`,
`website`, `description`, `image_count`, and `images[]`.

Each entry in `images[]`:

| field | meaning |
|-------|---------|
| `id` | image UUID (matches the file in `images/`) |
| `file` | relative path to the image file |
| `sort_order` | original display order |
| `quality_score` | 0–1 technical quality |
| `appeal_score` | 0–1 visual appeal |
| `usable` | whether the image passed usability checks |
| `usability_issues` | list of flagged issues (empty if none) |
| `subjects` | detected subjects (e.g. guest_room, pool_indoor, ambiance) |
| `description` | model-generated description of the image |
| `width`, `height` | pixel dimensions |

## The task

Candidates build a mechanism for image-placement scenarios using the images, the basic
hotel data, and the per-image evaluation metadata above.
