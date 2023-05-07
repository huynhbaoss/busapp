from django.urls import path, include
from . import views
from rest_framework import routers


router = routers.DefaultRouter()
router.register('Buses', views.BusesViewSet)
router.register('Payment', views.PaymentViewSet)
router.register('Delivery', views.DeliveryViewSet)
router.register('User', views.UserViewSet)
router.register('TransportCompany', views.TransportCompanyViewSet)
router.register('Review', views.ReviewViewSet)


urlpatterns = [
    path('', include(router.urls)),
]
