from django.urls import path

from .views import *

urlpatterns = [

    path("chats/<int:package_id>/create", CreateChatsView.as_view(), name="chats.create"),
    path('chats/', IndexChatsView.as_view(), name='chats.index'),
    path('chats/<int:chat_id>/end', EndChatsView.as_view(), name='chats.end'),
    path('chats/check', CheckChatsView.as_view(), name='chats.check'),
    path('chats/check-coupon', CheckCouponsView.as_view(), name='chats.coupons.check'),

]
