from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from shop.models import Package


class Chat(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sender_chats")  # it's a customer
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="receiver_chats")  # it's a pharmacist
    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name="chats", default=None)
    accepted = models.BooleanField(default=False)
    ended = models.BooleanField(default=False)
    useful = models.IntegerField(default=0)  # -1 = negative  , 1 = positive, 0 = not rated

    pending_acceptance = models.BooleanField(default=True)
    date = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "chats"


class Message(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="messages", default=None)
    text = models.TextField()
    date = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "messages"