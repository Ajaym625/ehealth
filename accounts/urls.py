from django.urls import path
from accounts.views import *
urlpatterns = [

    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("", HomeView.as_view(), name="home"),

    path("addresses/", IndexAddressesView.as_view(), name="addresses.index"),
    path("addresses/create", CreateAddressesView.as_view(), name="addresses.create"),
    path("addresses/<int:address_id>/destroy", DestroyAddressesView.as_view(), name="addresses.destroy"),
]
