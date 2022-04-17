import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import User
from django.db.models import Q

from accounts.models import Seller, Customer
from chat.models import Chat, Message
from shop.models import Coupon


class ChatConsumer(AsyncWebsocketConsumer):

    @database_sync_to_async
    def create_message(self, chat_id, text, author_id):
        chat = Chat.objects.filter(Q(pk=chat_id) & (Q(sender=author_id) | Q(receiver=author_id))).first()

        if chat:
            if chat.receiver_id == author_id and chat.pending_acceptance and not chat.accepted:
                chat.pending_acceptance = False
                chat.accepted = True
                chat.save()

            return Message.objects.create(chat_id=chat_id, text=text, author_id=author_id)

        return None

    @database_sync_to_async
    def check_status(self, connect=True):
        user_id = self.scope["user"].id
        user = User.objects.get(pk=user_id)

        if hasattr(user, "seller"):
            if user.seller.is_pharmacist:
                seller = Seller.objects.get(user=user)
                seller.chat_online = connect
                seller.save()

        else:
            customer = Customer.objects.get(user=user)
            customer.chat_online = connect
            customer.save()
            if not connect: # customer is closing chat
                chat = Chat.objects.get(pk=self.chat_id)

                if not chat.ended:
                    chat.ended = True

                messages = Message.objects.filter(Q(chat=chat) & Q(author_id=chat.receiver_id))
                coupon = Coupon.objects.get(chat=chat)

                if not coupon.usable:
                    coupon.usable = True if len(messages) >= 1 else False

                chat.save()
                coupon.save()


    async def connect(self):

        self.chat_id = self.scope['url_route']['kwargs']['chat_id']

        print("CONNECTED")
        await self.check_status()

        self.room_group_name = 'chat_%s' % self.chat_id

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        print("DISCONNECTED")
        await self.check_status(connect=False)
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        sender_id = self.scope["user"].id
        # chat, chat_created = await self.create_chat(sender_id, receiver_id, package_id)

        message_object = await self.create_message(self.chat_id, message, sender_id)
        # Send message to room group
        if message_object is not None:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'sender_id': self.scope["user"].id,
                    'date': message_object.date.strftime('%d/%m/%Y, %H:%M:%S'),
                }
            )

    # Receive message from room group
    async def chat_message(self, event):
        message = event['message']
        sender_id = event['sender_id']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'date': event['date'],
            'sender_id': sender_id
        }))