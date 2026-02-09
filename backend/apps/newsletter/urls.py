from django.urls import path

from .views import SubscribeView

urlpatterns = [
    path('subscribe/', SubscribeView.as_view(), name='newsletter-subscribe'),
]
