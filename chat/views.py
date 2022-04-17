from django.utils import timezone

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import RedirectView, TemplateView
from django.views.generic.base import View
from rdoclient import RandomOrgClient

from accounts.models import Seller, Customer
from chat.models import Chat, Message
from classes.Utilities import Utilities
from shop.models import Package, Coupon


@method_decorator(Utilities.AUTH_DECORATORS, name='dispatch')
class IndexChatsView(TemplateView):
    template_name = "chat/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        user = self.request.user
        if Utilities.is_pharmacist(self.request):
            context["chats"] = Chat.objects.filter(receiver=user).order_by("-date")
            pharmacist = Seller.objects.get(user=user)
            if not pharmacist.chat_online:
                pharmacist.chat_online = True
                pharmacist.save()
        elif Utilities.is_customer(self.request):
            context["chats"] = Chat.objects.filter(sender=user).order_by("-date")
            customer = Customer.objects.get(user=user)
            if not customer.chat_online:
                customer.chat_online = True
                customer.save()
        elif Utilities.is_admin(self.request):
            self.template_name = "shop/admin/chat/index.html"
            context["chats"] = Chat.objects.all().order_by("-date")
        else:
            raise PermissionDenied
        return context


@method_decorator(Utilities.AUTH_DECORATORS, name='dispatch')
class IndexPharmacistsView(TemplateView):
    template_name = "shop/admin/pharmacists/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        if Utilities.is_admin(self.request):
            context["pharmacists"] = Seller.objects.filter(is_pharmacist=True)
        else:
            raise PermissionDenied
        return context


@method_decorator(Utilities.AUTH_DECORATORS, name='dispatch')
class ApprovePharmacistsView(View):

    def post(self, request, *args, **kwargs):
        if request.is_ajax():
            pharmacist_to_approve_id = request.POST.get("pharmacist_id")
            pharmacist = Seller.objects.get(id=pharmacist_to_approve_id)
            pharmacist.approved = True
            pharmacist.save()

            return JsonResponse({"message": "saved"})

@method_decorator(Utilities.CUSTOMER_AUTH_TRANSACTION_DECORATORS, name='dispatch')
class EndChatsView(View):

    def post(self, request, *args, **kwargs):
        if request.is_ajax():
            chat_id = kwargs['chat_id']
            useful = request.POST.get('useful')

            chat = Chat.objects.filter(Q(sender=request.user) & Q(id=chat_id)).first()
            coupon = Coupon.objects.get(chat=chat)
            if chat:
                chat.ended = True
                chat.useful = useful
                chat.save()
                if useful == 1:
                    coupon.usable = True

                coupon.save()

                return JsonResponse(data={"message": "ended"})

            return JsonResponse(data={"message": "Not allowed"}, status=403)


@method_decorator(Utilities.CUSTOMER_AUTH_TRANSACTION_DECORATORS, name='dispatch')
class CreateChatsView(RedirectView):

    def post(self, request, *args, **kwargs):
        package_id = kwargs["package_id"]

        try:
            self.pattern_name = 'chats.index'
            package = Package.objects.get(pk=package_id)
            sender_id = request.user.id

            # receivers are all pharmacists, a random receiver will be chosen to act as an help desk
            receivers = list(User.objects.filter(seller__is_pharmacist=True, seller__chat_online=True))
            receivers_len = len(receivers)

            if receivers_len:

                try:
                    chat = Chat.objects.get(sender_id=sender_id,
                                            package_id=package_id,
                                            accepted=False,
                                            pending_acceptance=True,
                                            ended=False)

                except ObjectDoesNotExist:
                    random_org_client = RandomOrgClient(settings.RANDOM_ORG_API_KEY)
                    if receivers_len > 1:
                        random_numbers = random_org_client.generate_integers(1, 0, receivers_len - 1)
                        random_number = random_numbers[0]
                    else:
                        random_number = 0
                    receiver_id = receivers[random_number].id

                    chat = Chat.objects.create(sender_id=sender_id, receiver_id=receiver_id, package_id=package_id)
                    coupon_code = Utilities.generate_help_desk_coupon(chat.id)
                    coupon = Coupon.objects.create(code=coupon_code, is_discounted=True, discount_percentage=2, fee_percentage=4, chat=chat)

                    request_text = f"Ciao, vorrei avere ulteriori informazioni riguardo {package.product.name} - {package}"

                    request_message = Message.objects.create(chat=chat, author_id=sender_id, text=request_text)
            else:
                messages.info(request, "Nessun farmacista online, riprovare piu tardi!")
                return redirect(reverse_lazy('products.show', kwargs={'pk': package.product_id}))

        except ObjectDoesNotExist:
            self.pattern_name = 'chats.index'

        return super(CreateChatsView, self).post(request)


@method_decorator(Utilities.SELLER_AUTH_TRANSACTION_DECORATORS, name='dispatch')
class CheckChatsView(View):

    def post(self, request, *args, **kwargs):
        if request.is_ajax():
            already_existing_chat_ids = request.POST.getlist("chat_ids[]")

            new_chats = list(Chat.objects.filter(Q(receiver=request.user) & ~Q(id__in=already_existing_chat_ids)))

            new_chats_data = []
            for new_chat in new_chats:
                data = {
                    "id": new_chat.id,
                    "sender_username": new_chat.sender.username,
                    "package": new_chat.package.__str__(),
                    "product_name": new_chat.package.product.name,
                    "coupon_code": new_chat.coupon.code,
                }

                new_chat_messages = Message.objects.filter(chat=new_chat).order_by("-date")
                messages = []

                for new_chat_message in new_chat_messages:
                    message = {
                        "text": new_chat_message.text,
                        "date": new_chat_message.date.strftime("%d/%m/%Y, %H:%M:%S")
                    }

                    messages.append(message)

                data["messages"] = messages

                new_chats_data.append(data)

            return JsonResponse({"new_chats": new_chats_data})


@method_decorator(Utilities.CUSTOMER_AUTH_TRANSACTION_DECORATORS, name='dispatch')
class CheckCouponsView(View):

    def post(self, request, *args, **kwargs):
        if request.is_ajax():
            coupon_code = request.POST.get('coupon')
            coupon = Coupon.objects.filter(Q(code=coupon_code) & Q(usable=True)).first()

            return JsonResponse({"discount_percentage": coupon.discount_percentage if coupon is not None else 0 })