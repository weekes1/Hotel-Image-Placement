from django.urls import path

from . import views


urlpatterns = [
    path(
        "<str:hotel_id>/image-presentation",
        views.image_presentation,
        name="image-presentation",
    ),
]