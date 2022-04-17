from django.conf.urls import url
from django.contrib import admin
from django.urls import path, include

from chat.views import IndexChatsView, IndexPharmacistsView, ApprovePharmacistsView
from .views import *
urlpatterns = [
    url("seller/", include([
        path("products/", IndexProductsView.as_view(), name="seller.products.index"),
        path("products/<int:pk>/", ShowProductsView.as_view(), name="seller.products.show"),
        path("products/check/", CheckProductsView.as_view(), name="seller.products.check"),
        path("products/create/", CreateProductsView.as_view(), name="seller.products.create"),
        path("products/<int:pk>/packages/create/", CreateProductsPackagesView.as_view(), name="seller.products.packages.create"),
        path("products/<int:pk>/images/create/", CreateProductsImagesView.as_view(), name="seller.products.images.create"),
        path("products/<int:product_id>/packages/<int:package_id>/sponsorships/create/", CreateProductsPackagesSponsorshipsView.as_view(), name="seller.products.packages.sponsorships.create"),
        path("products/<int:product_id>/packages/<int:package_id>/sponsorships/destroy/",DestroyProductsPackagesSponsorshipsView.as_view(), name="seller.products.packages.sponsorships.destroy"),

        path("orders/", IndexOrdersView.as_view(), name="seller.orders.index"),
        path("orders/help_desk/", IndexOrdersHelpDeskView.as_view(), name="seller.orders.help_desk.index"),
        path("orders/<int:pk>/", ShowOrdersView.as_view(), name="seller.orders.show"),
        path("orders/<int:order_id>/edit/", EditOrdersView.as_view(), name="seller.orders.edit"),
        path("orders/<int:order_id>/shipments/<int:shipment_id>/edit/", EditOrdersShipmentsView.as_view(), name="seller.orders.shipments.edit"),

        path("dashboard/", DashboardView.as_view(), name="seller.dashboard"),

    ]), {'seller': True}),

    url("", include([
        path("products/<int:pk>/", ShowProductsView.as_view(), name="products.show"),
        path("products/", IndexProductsView.as_view(), name="products.index"),
        path("products/sellers/<int:seller_id>", IndexProductsSellersView.as_view(), name="products.sellers.index"),

        path("products/<int:product_id>/packages/<int:package_id>/offers", IndexProductsPackagesOffersView.as_view(), name="products.packages.offers.index"),

        path("cart/", ShowCartPackagesView.as_view(), name="cart.show"),
        path("cart/prescriptions/check", CheckCartPrescriptionsView.as_view(), name="cart.prescriptions.check"),
        path("cart/create/", CreateCartPackagesView.as_view(), name="cart.package.create"),
        path("cart/<int:package_id>/edit", EditCartPackagesView.as_view(), name="cart.package.edit"),
        path("cart/<int:package_id>/destroy", DestroyCartPackagesView.as_view(), name="cart.package.destroy"),

        path("orders/", IndexOrdersView.as_view(), name="orders.index"),
        path("orders/export", ExportOrdersDataView.as_view(), name="orders.export"),

        path("orders/checkout/pay", OrdersCheckoutPayView.as_view(), name="orders.checkout.pay"),
        path("orders/checkout/summary", OrdersCheckoutSummaryView.as_view(), name="orders.checkout.summary"),
        path("orders/<int:pk>", ShowOrdersView.as_view(), name="orders.show"),
        path("orders/<int:order_id>/feedbacks/create", CreateOrdersFeedbacksView.as_view(), name="orders.feedbacks.create"),
        path("profiles/<int:pk>", ShowProfilesView.as_view(), name="profiles.show")
    ]), {"seller": False}),

    url("administration/", include([
        path("orders/", IndexOrdersView.as_view(), name="administration.orders.index"),
        path("orders/export", ExportOrdersDataView.as_view(), name="administration.orders.export"),
        path("orders/<int:pk>", ShowOrdersView.as_view(), name="administration.orders.show"),
        path('chats/', IndexChatsView.as_view(), name='administration.chats.index'),
        path('pharmacists/', IndexPharmacistsView.as_view(), name='administration.pharmacists.index'),
        path('pharmacists/approve', ApprovePharmacistsView.as_view(), name='administration.pharmacists.approve'),
    ]), {"seller": False}),
]