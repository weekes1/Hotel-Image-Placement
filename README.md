# Hotel-Image-Placement

Contextually placing hotel images given user specifications.

## How to run

Requires Python 3.10–3.14. From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) for the visual demo.
Choose a hotel or switch between **Member** and **Curator** to update automatically.
If JavaScript is disabled, use **View presentation** to apply your choices. Click any photo
to open it at full size, or **View JSON** to inspect the HTTP response.
The demo uses a Django template and a small CSS file; no Node.js setup is needed.
Keep the supplied dataset at `data/paris-hotels-image-placement/` so the metadata
and local image files can be loaded.

Replace `{hotel_id}` with a hotel's `id` from the supplied dataset, then open
either URL in your browser:

```text
http://127.0.0.1:8000/hotels/{hotel_id}/image-presentation?audience=curator
http://127.0.0.1:8000/hotels/{hotel_id}/image-presentation?audience=member
```

To run the tests, use a second terminal with the virtual environment activated:

```bash
python manage.py test
```

## Selection and ordering approach

### General 

For image quality, I chose to balance quality and appeal equally. This can be seen in the def image_strength(image)

Unusable images are never used.

### Curator Selection

Room and dining images leading. Other images follow. Apply variety rule.

### member selection

Select one property hero, followed by separate amenities and dining galleries containing up to five images each. Images cannot repeat within the presentation. Hero selection prioritizes property relevance, then quality and appeal.

#### Variety

For a hotel, after ranking etc, we run the image type names to make sure that type of image hasn't been seen before if we but up on the same image type, we look for a new image type that isn't too much weaker in quality (0.05).

## Fallback behaviour and assumptions

I built this small backend to somewhat mirror what it would be like to sanitize incoming requests in a real production backend for security reasons. In practice this would look more like guards and request shape validation. We are assuming that meta data accurate describes the pictures and that the images actually exist.

- no building / property: try lobby garden, terrace, view or lounge
- no hero candidate: try strongest usable image
- no eligible image: return nothing
- missing image id: use the file name
- no image id or file name: exclude
- missing field: treat as empty
- missing score: treat as 0
- missing or invalid subjects: treat as no subjects


## Improvements

With more time, there are three main areas in which I can improve this project: 

1. Productionization: 

I would use Docker to containerise the code for machine to machine stability. I would deploy this so that people could provide feedback. I would add a full login, sign in and authentication/ authorization flow -- implement JWT tokens etc. 

2. General Product Enhancements: 

Instead of using a static data set, I would find an API that enables me have a wider selection of hotels and potentially pick hotels based on city as well.

3. Image selection enhancements: 

If I were to try and turn this into a real product, I would improve the image selection in two ways: 

i. I would conduct some user testing to validate that the image selection procedure is functional in practice. 
ii. I would implement some NLP/ LLM techniques in order to actually make use of the image description. If i had more information on the user, I would potentially try to match the image description given user preference and assign some sort of value to that instead of just using quality and appeal score. 

## approximate time spent: 3.5 hours
