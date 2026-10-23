from django.urls import path

from . import views


urlpatterns = [
    path("<str:hotel_id>/images/<str:filename>", views.hotel_image, name="hotel-image"),
    path(
        "<str:hotel_id>/image-presentation",
        views.image_presentation,
        name="image-presentation",
    ),
]
