from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.db import connection, transaction
from django.db.models import F, Q, Sum
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404, Http404
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import ListView, TemplateView, DetailView, FormView, RedirectView
from more_itertools import chunked
from accounts.models import Address, Seller
from chat.models import Chat
from classes.Utilities import Utilities
import django_excel as excel
from shop.forms import CreateProductsForm, CreateProductsPackagesForm, CreateProductsImagesForm, CheckProductsForm
from shop.models import Product, Package, Order, PackageCart, Category, Image, PackageOrder, Status, OrderAddress, \
    Courier, Shipment, Excipient, Illness, ActiveSubstance, SponsoredPackage, Feedback, Coupon


def index_product_categories(request):
    # getting only those categories that have at least one product linked
    return {"product_categories": Category.objects.filter(pk__in=Product.objects.only('category').distinct())}


@method_decorator(Utilities.SELLER_AUTH_DECORATORS, name='dispatch')
class DashboardView(TemplateView):

    def get_context_data(self, **kwargs):
        context = super(DashboardView, self).get_context_data()
        if Utilities.as_seller(self.kwargs):
            if Utilities.is_pharmacist(self.request) or Utilities.is_pharmaceutical_company(self.request):
                self.template_name = "shop/seller/dashboard.html"

                seller = self.request.user.seller
                orders = Order.objects.filter(seller=seller)
                context["total_orders"] = orders.count()
                total_shipments_cost = Shipment.objects.filter(order__in=orders).aggregate(cost=Sum('cost'))
                total_proceeds = orders.aggregate(total_proceeds=Sum('total_price') - total_shipments_cost['cost'])["total_proceeds"]
                context["total_proceeds"] = 0 if total_proceeds is None else total_proceeds
                context["average_proceeds_per_order"] = 0 if context["total_orders"] == 0 else round(context["total_proceeds"]/context["total_orders"],2)
                recent_orders = orders.order_by('-date')[:4]  # get last 4 orders
                context["recent_orders"] = recent_orders if len(recent_orders) else None
                monthly_proceeds = [0] * 12
                monthly_proceeds_data = list(orders.values(month=F('date__month')).annotate(total_proceeds=Sum('total_price')).order_by('date__month'))

                for monthly_proceeds_datum in monthly_proceeds_data:
                    monthly_proceeds[int(monthly_proceeds_datum["month"]) - 1] = float(monthly_proceeds_datum["total_proceeds"])

                context["monthly_proceeds"] = monthly_proceeds

        return context


class ShowProductsView(DetailView):
    model = Product

    def get_context_data(self, **kwargs):
        context = super(ShowProductsView, self).get_context_data()
        product = context["product"]
        product_id = product.id
        cursor = connection.cursor()

        if Utilities.as_seller(self.kwargs):
            if Utilities.is_pharmacist(self.request) or Utilities.is_pharmaceutical_company(self.request):
                self.template_name = "shop/seller/products/show.html"
                context["packages"] = Package.objects.filter(
                    Q(product=product) & Q(seller=self.request.user.seller)).order_by('price')
            else:
                raise PermissionDenied

        else:
            self.template_name = "shop/customer/products/show.html"
            pharmacist_pharmaceutical_company_query = """  
                        select sellers.business_name as business_name, sellers.user_id as user_id, products.id as product_id,
                               packages.id as package_id, packages.available_quantity, packages.type, packages.amount,
                               packages.dosage, packages.is_sponsored, x.min_price as price
                        
                        from products join
                        
                             packages on packages.product_id = products.id join
                        
                             (select product_id, min(price) as min_price
                              from packages join
                                   sellers on sellers.id = packages.seller_id
                              where packages.available_quantity > %s and sellers.is_pharmacist = %s
                              group by amount, dosage, type, product_id) as x
                        
                             on x.product_id = products.id and price = x.min_price
                                      join sellers on sellers.id = packages.seller_id
                        where products.id = %s and products.needs_prescription = %s order by packages.is_sponsored DESC, price;
                        """
            if Utilities.is_pharmacist(self.request):
                cursor.execute(pharmacist_pharmaceutical_company_query, [0, False, product_id, False])

            elif Utilities.is_pharmaceutical_company(self.request):
                cursor.execute(pharmacist_pharmaceutical_company_query, [0, True, product_id, True])

            else:
                cursor.execute("""  
                    select sellers.business_name, sellers.user_id as user_id, products.id as product_id,
                    packages.id as package_id, packages.available_quantity, packages.type, packages.amount, packages.dosage,
                    packages.is_sponsored, x.min_price as price
                    from products join

                         packages on packages.product_id = products.id join
                         (select product_id, min(price) as min_price from packages where available_quantity > 0 
                          group by amount, dosage, type, product_id) as x
                         on x.product_id = products.id and price = x.min_price

                    join sellers on sellers.id = packages.seller_id
                    where products.id = %s order by packages.is_sponsored DESC, price ;       
                """, [product_id])

            min_price_packages = Utilities.dict_fetchall(cursor)

            if len(min_price_packages) == 0:
                raise Http404()

            # same packages with more expensive prices from other sellers
            # using first package of min_price_packages to be shown on the page,
            # other packages will be shown on user click
            main_min_price_package = min_price_packages[0]

            # we get the first 4 offers for readability purposes
            context["offers"] = IndexProductsPackagesOffersView.get_offers(self.request,
                                                                           product_id,
                                                                           main_min_price_package["package_id"],
                                                                           main_min_price_package["type"],
                                                                           main_min_price_package["amount"],
                                                                           main_min_price_package["dosage"],
                                                                           main_min_price_package["price"],
                                                                           max_offers=4)
            context["packages"] = min_price_packages

        context["images"] = Image.objects.filter(product=product)
        context["category_name"] = Category.objects.get(pk=product.category_id).name

        return context


@method_decorator(Utilities.CUSTOMER_AUTH_DECORATORS, name='dispatch')
class IndexProductsPackagesOffersView(View):

    @staticmethod
    def get_offers(request, product_id, package_id, package_type, amount, dosage, price, max_offers=-1):

        offers = Package.objects.filter(
            Q(product_id=product_id) &
            Q(type=package_type) &
            Q(amount=amount) &
            Q(dosage=dosage) &
            Q(price__gte=price)
        )

        if Utilities.is_pharmacist(request):
            offers = offers.filter(Q(seller__is_pharmacist=False) & Q(product__needs_prescription=False))

        elif Utilities.is_pharmaceutical_company(request):
            offers = offers.filter(Q(seller__is_pharmacist=True) & Q(product__needs_prescription=True))

        # if max_offers is negative it means we want all offers with the one with the minimum price included
        # else we exclude the one with the minimum price
        if max_offers < 0:
            offers = list(offers.order_by('price').values('id',
                                                          'product_id',
                                                          'product__name',
                                                          'amount',
                                                          'dosage',
                                                          'price',
                                                          business_name=F('seller__business_name')))
        else:
            offers = list(offers.filter(~Q(id=package_id)).order_by('price').values('id',
                                                                                    'product_id',
                                                                                    'product__name',
                                                                                    'type',
                                                                                    'amount',
                                                                                    'dosage',
                                                                                    'price',
                                                                                    business_name=F('seller__business_name')))[:max_offers]
        return offers if len(offers) else None

    def get(self, request, *args, **kwargs):

        package_id = self.kwargs.get("package_id")
        package = get_object_or_404(Package, pk=package_id)
        offers = IndexProductsPackagesOffersView.get_offers(request,
                                                            self.kwargs.get("product_id"),
                                                            package_id,
                                                            package.type,
                                                            package.amount,
                                                            package.dosage,
                                                            package.price
                                                            )

        data = {"offers": offers,
                "content_title": "Offerte per: " + Product.objects.get(pk=package.product_id).name + " - " + package.__str__()
                }
        return render(request, "shop/customer/products/packages/offers/index.html", data)


    def post(self, request, *args, **kwargs):
        data = {"offers": IndexProductsPackagesOffersView.get_offers(request,
                                                                     self.kwargs.get("product_id"),
                                                                     self.kwargs.get("package_id"),
                                                                     self.request.POST.get("type"),
                                                                     self.request.POST.get("amount"),
                                                                     self.request.POST.get("dosage"),
                                                                     self.request.POST.get("price"),
                                                                     max_offers=int(self.request.POST.get("max_offers")))}
        return JsonResponse(data)


@method_decorator(Utilities.SELLER_AUTH_TRANSACTION_DECORATORS, name='dispatch')
class CheckProductsView(FormView):
    form_class = CheckProductsForm
    template_name = "shop/seller/products/check.html"

    def get_success_url(self):
        aic = self.request.POST.get('aic')
        try:
            product = Product.objects.values('id', 'name', 'aic').get(aic=aic)
        except ObjectDoesNotExist:
            product = None

        if product is None:
            self.request.session['product_to_create_aic'] = self.request.POST.get('aic')
            return reverse_lazy('seller.products.create')
        else:
            return reverse_lazy('seller.products.packages.create', kwargs={"pk": product["id"]})


@method_decorator(Utilities.SELLER_AUTH_TRANSACTION_DECORATORS, name='dispatch')
class CreateProductsView(FormView):
    form_class = CreateProductsForm
    template_name = 'shop/seller/products/create.html'
    MAX_EXTRA_FIELDS = 5

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super(CreateProductsView, self).get_form_kwargs()
        form_kwargs["MAX_EXTRA_FIELDS"] = self.MAX_EXTRA_FIELDS
        return form_kwargs

    def form_valid(self, form):
        product = form.save(commit=False)
        active_substance_name = form.cleaned_data["active_substance"]
        active_substance, created = ActiveSubstance.objects.update_or_create(name=active_substance_name)

        product.active_substance = active_substance
        product = form.save()

        for i in range(self.MAX_EXTRA_FIELDS):
            excipient_name = form.cleaned_data[f"excipient_{i}"]
            excipient, created = Excipient.objects.update_or_create(name=excipient_name)

            illness_name = form.cleaned_data[f"illness_{i}"]
            illness, created = Illness.objects.update_or_create(name=illness_name)

            product.excipients.add(excipient)
            product.illnesses.add(illness)

        if 'product_to_create_aic' in self.request.session:
            self.request.session.pop('product_to_create_aic')

        self.success_url = reverse_lazy('seller.products.packages.create', kwargs={'pk': product.id})
        return super(CreateProductsView, self).form_valid(form)


@method_decorator(Utilities.SELLER_AUTH_TRANSACTION_DECORATORS, name='dispatch')
class CreateProductsPackagesView(FormView):
    form_class = CreateProductsPackagesForm
    template_name = 'shop/seller/products/packages/create.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context["content_title"] = "Aggiungi pacchetto per " + Product.objects.get(pk=self.kwargs.get("pk")).name
        return context

    def form_valid(self, form):
        product_id = self.kwargs.get("pk")
        package = form.save(commit=False)
        package.product_id = product_id
        package.seller = self.request.user.seller
        package = form.save()

        # images are not needed if at least 1 already exists
        if Image.objects.filter(product_id=product_id).count():
            self.success_url = reverse_lazy('seller.products.show', kwargs={'pk': product_id})
        else:
            self.success_url = reverse_lazy('seller.products.images.create', kwargs={'pk': product_id})

        return super(CreateProductsPackagesView, self).form_valid(form)


@method_decorator(Utilities.SELLER_AUTH_TRANSACTION_DECORATORS, name='dispatch')
class CreateProductsImagesView(FormView):
    template_name = "shop/seller/products/images/create.html"
    form_class = CreateProductsImagesForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context["content_title"] = "Aggiungi immagini per " + Product.objects.get(pk=self.kwargs.get("pk")).name
        return context

    def post(self, request, *args, **kwargs):
        product_id = kwargs["pk"]
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        images = request.FILES.getlist('file')

        if form.is_valid():
            self.success_url = reverse_lazy('seller.products.show', kwargs={"pk": product_id})
            product_has_images = Image.objects.filter(product_id=product_id).count()
            for i in range(len(images)):

                if product_has_images:
                    is_main = False
                else:
                    is_main = i == 0

                Image.objects.create(file=images[i], is_main=is_main, product_id=product_id)
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


@method_decorator(Utilities.CUSTOMER_AUTH_TRANSACTION_DECORATORS, name='dispatch')
class ShowCartPackagesView(View):

    def get(self, request, **kwargs):
        customer = request.user.customer
        customer_cart = customer.cart

        packages = PackageCart.objects.filter(Q(cart=customer_cart) & Q(package__product__images__is_main=True))
        prescription_needed = packages.filter(Q(package__product__needs_prescription=True)).count() > 0

        packages = packages.values(
            'requested_quantity',
            'package_id',
            product_id=F('package__product__id'),
            business_name=F('package__seller__business_name'),
            name=F('package__product__name'),
            needs_prescription=F('package__product__needs_prescription'),
            price=F('package__price'),
            available_quantity=F('package__available_quantity'),
            amount=F('package__amount'),
            type=F('package__type'),
            dosage=F('package__dosage'),
            file=F('package__product__images__file'),
            seller_user_id=F('package__seller__user_id'),
            seller_blockchain_address=F('package__seller__blockchain_address')

        )
        packages_len = len(packages)
        return render(request, "shop/customer/cart/show.html", {
            "packages": None if packages_len == 0 else list(chunked(packages, settings.PRODUCTS_PER_ROW)),
            "content_title": "Carrello",
            "total_packages": packages_len,
            "prescription_needed": prescription_needed
        })


class CheckCartPrescriptionsView(View):
    DELIMITER = ";\n"

    def post(self, request, *args, **kwargs):
        products_with_prescription_names = self.request.POST.get("productsWithPrescriptionsNames").split(self.DELIMITER)

        products_with_prescription_names_length = len(products_with_prescription_names)
        if products_with_prescription_names[products_with_prescription_names_length - 1] == '':
            products_with_prescription_names[products_with_prescription_names_length - 1].pop()

        cart_products_ids = PackageCart.objects.filter(Q(cart=request.user.customer.cart)).values_list('package__product_id')
        products = Product.objects.filter(Q(id__in=cart_products_ids) & Q(needs_prescription=True))
        products_with_prescription_names_found = 0

        for i in range(0, len(products_with_prescription_names)):
            product_with_prescription_name = products_with_prescription_names[i]
            if products.filter(Q(name=product_with_prescription_name)):
                products_with_prescription_names_found += 1

        prescription_approved = products_with_prescription_names_found == len(products_with_prescription_names) == len(products)

        return JsonResponse({'message': prescription_approved})


@method_decorator(Utilities.CUSTOMER_AUTH_TRANSACTION_DECORATORS, name='dispatch')
class CreateCartPackagesView(View):

    def post(self, request, **kwargs):
        if request.is_ajax():
            package_id = request.POST.get('requested_package_id')
            customer = request.user.customer
            customer_cart = customer.cart

            requested_quantity = int(request.POST.get('requested_quantity'))

            try:
                packages_carts_pivot = PackageCart.objects.get(cart_id=customer_cart.id, package_id=package_id)

            except ObjectDoesNotExist:
                packages_carts_pivot = PackageCart(
                    cart_id=customer_cart.id,
                    package_id=package_id,
                    requested_quantity=requested_quantity
                )

            available_quantity = packages_carts_pivot.package.available_quantity
            if requested_quantity > available_quantity:
                return JsonResponse({"message": "La quantità richiesta supera la quantità disponibile!"}, status=403)
            else:
                packages_carts_pivot.requested_quantity = requested_quantity
                packages_carts_pivot.save()
                return JsonResponse({"message": "Prodotto aggiunto al carrello!"}, status=200)


@method_decorator(Utilities.CUSTOMER_AUTH_TRANSACTION_DECORATORS, name='dispatch')
class EditCartPackagesView(View):

    def post(self, request, **kwargs):
        if request.is_ajax():
            customer_cart = request.user.customer.cart
            package_id = kwargs["package_id"]
            try:
                package_cart = PackageCart.objects.values(
                    'requested_quantity',
                    'package__available_quantity',
                    'id'
                ).get(Q(cart=customer_cart) & Q(package_id=package_id))

                requested_quantity = int(request.POST["requested_quantity"])
                available_quantity = package_cart["package__available_quantity"]

                if requested_quantity > available_quantity:
                    return JsonResponse(
                        {'error': "La quantità richiesta non è disponibile. Max: " + str(available_quantity),
                         'old_quantity': package_cart["requested_quantity"]},
                        status=403)
                else:
                    PackageCart.objects.filter(Q(cart=customer_cart) & Q(package_id=package_id)).update(
                        requested_quantity=requested_quantity)
                    return JsonResponse({"message": "Quantità aggiornata"}, status=200)

            except:
                return JsonResponse({'error': "La risorsa richiesta non è accessibile per questo utente."}, status=403)


@method_decorator(Utilities.CUSTOMER_AUTH_TRANSACTION_DECORATORS, name='dispatch')
class DestroyCartPackagesView(View):

    def post(self, request, **kwargs):
        customer_cart = request.user.customer.cart
        PackageCart.objects.get(cart=customer_cart, package_id=kwargs["package_id"]).delete()
        return redirect(reverse_lazy('cart.show'))


@method_decorator(Utilities.CUSTOMER_AUTH_TRANSACTION_DECORATORS, name='dispatch')
class OrdersCheckoutSummaryView(ListView):
    template_name = 'shop/customer/orders/checkout/summary.html'
    model = PackageCart
    context_object_name = 'packages_carts'

    def get_queryset(self):
        base_query = super().get_queryset()
        packages_carts = base_query.filter(cart=self.request.user.customer.cart)
        return packages_carts if packages_carts.count() > 0 else None

    def get_context_data(self, **kwargs):
        context = super(OrdersCheckoutSummaryView, self).get_context_data()
        context["shipping_addresses"] = Address.objects.filter(
            Q(customer=self.request.user.customer) & Q(is_shipping=True))

        context["billing_addresses"] = Address.objects.filter(
            Q(customer=self.request.user.customer) & Q(is_billing=True))

        context["content_title"] = "Riepilogo"
        context["total_price"] = None

        if context["packages_carts"] is not None:
            context["total_price"] = context["packages_carts"].aggregate(total_price=Sum(F('package__price') * F('requested_quantity')))[
                "total_price"]

        context["couriers"] = Courier.objects.all()
        context["total_price"] += context["couriers"].first().standard_cost

        return context

    def render_to_response(self, context, **response_kwargs):
        if context["packages_carts"] is None:
            return redirect(reverse_lazy('cart.show'))

        if not (context["shipping_addresses"].count() and context["billing_addresses"].count()):
            self.request.session['next'] = self.request.path
            return redirect('addresses.create')

        return super(OrdersCheckoutSummaryView, self).render_to_response(context)


@method_decorator(Utilities.CUSTOMER_AUTH_TRANSACTION_DECORATORS, name='dispatch')
class OrdersCheckoutPayView(View):

    def get(self,request, **kwargs):
        return redirect('orders.checkout.summary')

    def post(self, request, **kwargs):
        print(self.request.POST)
        customer = request.user.customer
        customer_cart = customer.cart
        coupon_code = request.POST.get("coupon")
        coupon = None

        if not coupon_code == "":
            try:
                coupon = Coupon.objects.get(Q(code=coupon_code) & Q(usable=True) & Q(chat__sender_id=request.user))
            except ObjectDoesNotExist:
                messages.info(request, "Non puoi usare questo coupon!")
                return redirect('orders.checkout.summary')


        # TODO: implement payment systems
        # code for payment here
        # code for payment here
        # code for payment here

        payment_completed = True

        if payment_completed:

            packages_cart = PackageCart.objects.filter(cart=customer_cart)

            # creating different orders for each different seller
            sellers = packages_cart.values('package__seller').distinct()
            for seller_data in sellers:
                packages = packages_cart.filter(package__seller=seller_data["package__seller"]).values(
                    'requested_quantity',
                    'package__price',
                    'package_id',
                    'package__vat_price',
                    'package__vat_percentage',
                    'package__is_sponsored',
                    'package__sponsored_package__sponsorship_fee_percentage',
                    'package__seller__blockchain_address'
                )

                # total price is still 0, it will be updated for each package price
                total_price = 0
                total_vat_price = 0

                order = Order.objects.create(customer=customer,
                                             total_price=total_price,
                                             total_vat_price=total_vat_price,
                                             status=Status.objects.get(name="PAGAMENTO EFFETTUATO"),
                                             seller_id=seller_data["package__seller"],
                                             )
                for package in packages:
                    seller_blockchain_address = package['package__seller__blockchain_address']


                    # updating available quantity to the bought package and adding package to the order
                    p = Package.objects.get(pk=package['package_id'])
                    package_sponsorship_percentage_fee = package['package__sponsored_package__sponsorship_fee_percentage']
                    if package_sponsorship_percentage_fee is None:
                        sponsorship_cost = 0
                    else:
                        sponsorship_cost = package['package__price'] * package_sponsorship_percentage_fee /100
                    if coupon is None:
                        coupon_cost = 0
                        coupon_code = None
                        is_discounted = False
                        total_price += package['requested_quantity'] * package['package__price']
                        total_vat_price += package['requested_quantity'] * package['package__vat_price']
                        discount_percentage = 0
                    else:
                        coupon_cost = package['package__price'] * coupon.fee_percentage / 100
                        coupon_code = coupon.code
                        is_discounted = coupon.is_discounted
                        coupon.usable = False
                        coupon.save()
                        total_price += package['requested_quantity'] * (package['package__price'] - package['package__price'] * coupon.discount_percentage/100)
                        total_vat_price += package['requested_quantity'] * (package['package__vat_price'] - package['package__vat_price'] * coupon.discount_percentage/100)
                        discount_percentage = coupon.discount_percentage
                    PackageOrder.objects.create(package=p,
                                                order=order,
                                                requested_quantity=package['requested_quantity'],
                                                price=package['package__price'],
                                                vat_price=package['package__vat_price'],
                                                vat_percentage=package['package__vat_percentage'],
                                                is_sponsored=package["package__is_sponsored"],
                                                sponsorship_cost=sponsorship_cost,
                                                coupon=coupon_code,
                                                is_discounted=is_discounted,
                                                coupon_cost=coupon_cost,
                                                discount_percentage=discount_percentage
                                                )
                    p.available_quantity = p.available_quantity - package['requested_quantity']
                    p.save()

                    order.total_price = total_price
                try:
                    # checking addresses validity
                    shipping_address_id = self.request.POST.get('shipping_address')
                    billing_address_id = self.request.POST.get('billing_address')
                    if shipping_address_id == billing_address_id:

                        address = Address.objects.get(Q(pk=shipping_address_id) & Q(customer=self.request.user.customer) &
                                                      Q(is_shipping=True) & Q(is_billing=True))
                        OrderAddress.objects.create(order=order,
                                                    address=address,
                                                    raw_address=address.__str__(),
                                                    further_info=address.further_info,
                                                    is_shipping=True,
                                                    is_billing=True)
                    else:
                        shipping_address = Address.objects.get(Q(pk=shipping_address_id) &
                                                               Q(customer=self.request.user.customer) &
                                                               Q(is_shipping=True))

                        billing_address = Address.objects.get(Q(pk=billing_address_id) &
                                                              Q(customer=self.request.user.customer) &
                                                              Q(is_billing=True))

                        OrderAddress.objects.create(order=order,
                                                    address=shipping_address,
                                                    raw_address=shipping_address.__str__(),
                                                    further_info=shipping_address.further_info,
                                                    is_shipping=True,
                                                    is_billing=False)

                        OrderAddress.objects.create(order=order,
                                                    address=billing_address,
                                                    raw_address=billing_address.__str__(),
                                                    is_shipping=False,
                                                    is_billing=True)

                    # checking courier validity
                    courier_id = self.request.POST.get('courier')
                    courier = Courier.objects.get(pk=courier_id)

                    order.total_price += courier.standard_cost
                    order.total_vat_price = total_vat_price
                    order.save()

                    Shipment.objects.create(cost=courier.standard_cost,
                                            courier=courier,
                                            order=order)
                except ObjectDoesNotExist:
                    transaction.set_rollback(True)
                    return redirect('orders.checkout.summary')

            packages_cart.delete()


            return redirect(reverse_lazy('orders.index'))


@method_decorator(Utilities.AUTH_DECORATORS, name='dispatch')
class IndexOrdersView(ListView):
    model = Order
    context_object_name = "orders"

    def get_queryset(self):
        orders = super().get_queryset()

        if Utilities.as_seller(self.kwargs):
            if Utilities.is_pharmacist(self.request) or Utilities.is_pharmaceutical_company(self.request):
                self.template_name = "shop/seller/orders/index.html"
                orders = orders.filter(seller=self.request.user.seller)
            else:
                raise PermissionDenied

        elif Utilities.is_admin(self.request):
            self.template_name = "shop/admin/orders/index.html"
        else:
            self.template_name = "shop/customer/orders/index.html"
            orders = orders.filter(customer=self.request.user.customer)

        return orders if orders.count() else None

    def get_context_data(self, **kwargs):
        context = super(IndexOrdersView, self).get_context_data()
        context["content_title"] = "Ordini"
        return context


@method_decorator(Utilities.SELLER_AUTH_DECORATORS, name='dispatch')
class IndexOrdersHelpDeskView(ListView):
    model = Order
    context_object_name = "orders"

    def get_queryset(self):
        orders = super().get_queryset()

        if Utilities.as_seller(self.kwargs):
            if Utilities.is_pharmacist(self.request):
                self.template_name = "shop/seller/orders/index.html"
                user = self.request.user
                all_seller_coupons = Coupon.objects.filter(chat__in=Chat.objects.filter(receiver=user))
                orders = Order.objects.filter(package__chats__coupon__in=all_seller_coupons)
            else:
                raise PermissionDenied

        elif Utilities.is_admin(self.request):
            self.template_name = "shop/admin/orders/index.html"

        return orders if orders.count() else None

    def get_context_data(self, **kwargs):
        context = super(IndexOrdersHelpDeskView, self).get_context_data()
        context["content_title"] = "Ordini help desk"
        return context


@method_decorator(Utilities.AUTH_DECORATORS, name='dispatch')
class ShowOrdersView(DetailView):
    model = Order

    def get_queryset(self):
        order = super(ShowOrdersView, self).get_queryset()

        if Utilities.as_seller(self.kwargs):
            self.template_name = "shop/seller/orders/show.html"

            if Utilities.is_pharmaceutical_company(self.request):
                return order.filter(seller=self.request.user.seller)
            elif Utilities.is_pharmacist(self.request):
                orders_ids = PackageOrder.objects.filter(coupon__isnull=False).values('order_id').distinct()
                return order.filter(Q(seller=self.request.user.seller) | Q(id__in=orders_ids))
            else:
                raise PermissionDenied

        elif Utilities.is_admin(self.request):
            self.template_name = "shop/admin/orders/show.html"
            return order
        else:
            self.template_name = "shop/customer/orders/show.html"
            return order.filter(customer=self.request.user.customer)

    def get_context_data(self, **kwargs):
        context = super(ShowOrdersView, self).get_context_data()
        order = context["order"]

        if Utilities.as_seller(self.kwargs):
            if Utilities.is_pharmacist(self.request) or Utilities.is_pharmaceutical_company(self.request):
                context["statuses"] = Status.objects.all()
                packages_order = PackageOrder.objects.filter(Q(order=order))
                context["packages_order"] = packages_order
                context["earned_fee"] = packages_order.aggregate(earned_fee=Sum('coupon_cost'))["earned_fee"]

        elif Utilities.is_admin(self.request):
            context["statuses"] = Status.objects.all()
            context["packages_order"] = PackageOrder.objects.filter(Q(order=order))
            total_sponsorship_cost= context["packages_order"].aggregate(total_sponsorship_cost=Sum('sponsorship_cost'))["total_sponsorship_cost"]
            context["total_sponsorship_cost"] = 0 if total_sponsorship_cost is None else total_sponsorship_cost
        else:
            context["packages_order"] = PackageOrder.objects.filter(Q(order=order) &
                                                                    Q(order__customer=self.request.user.customer))
            print( context["packages_order"])

        addresses = OrderAddress.objects.filter(order=order)
        context["billing_address"] = addresses.filter(is_billing=True).first()
        context["shipping_address"] = addresses.filter(is_shipping=True).first()
        context["content_title"] = f"Ordine #{order.id} del {order.date.strftime('%d/%m/%Y')}"

        return context


@method_decorator(Utilities.SELLER_AUTH_TRANSACTION_DECORATORS, name='dispatch')
class EditOrdersView(View):

    def post(self, request, **kwargs):
        if request.is_ajax() and Utilities.as_seller(self.kwargs):
            if Utilities.is_pharmacist(self.request) or Utilities.is_pharmaceutical_company(self.request):
                order_id = kwargs["order_id"]
                status_id = request.POST.get('status')
                try:
                    status = Status.objects.get(pk=status_id)
                    order = Order.objects.get(Q(pk=order_id) & Q(seller=request.user.seller))
                    order.status = status
                    order.save()
                    return JsonResponse({"message": "Stato dell'ordine aggiornato!"}, status=200)

                except ObjectDoesNotExist:
                    return JsonResponse({'message': "Non puoi modificare questo campo!"}, status=404)
            else:
                JsonResponse({"redirect": reverse_lazy('orders.show', kwargs={"pk": kwargs["order_id"]})}, status=302)


@method_decorator(Utilities.SELLER_AUTH_TRANSACTION_DECORATORS, name='dispatch')
class EditOrdersShipmentsView(View):

    def post(self, request, **kwargs):
        if request.is_ajax() and Utilities.as_seller(self.kwargs):
            if Utilities.is_pharmacist(self.request) or Utilities.is_pharmaceutical_company(self.request):
                order_id = kwargs["order_id"]
                shipment_id = kwargs['shipment_id']
                tracking_code = request.POST.get('tracking_code')

                try:
                    shipment = Shipment.objects.get(Q(pk=shipment_id) & Q(order_id=order_id) & Q(order__seller=request.user.seller))
                    shipment.tracking_code = tracking_code
                    shipment.save()
                    return JsonResponse({"message": "Codice di tracking aggiornato!"}, status=200)

                except ObjectDoesNotExist :
                    return JsonResponse({'message': "Non puoi modificare questo campo!"}, status=404)
            else:
                JsonResponse({"redirect": reverse_lazy('orders.show', kwargs={"pk": kwargs["order_id"]})}, status=302)


class IndexProductsView(TemplateView):

    def get_context_data(self, **kwargs):

        context = super().get_context_data()
        if Utilities.as_seller(kwargs):
            if Utilities.is_pharmacist(self.request) or Utilities.is_pharmaceutical_company(self.request):
                self.template_name = 'shop/seller/products/index.html'
        else:
            self.template_name = 'shop/customer/products/index.html'

        search_by = "all" if self.request.GET.get('search_by') is None else self.request.GET.get('search_by')
        data = IndexProductsView.search(self.request, kwargs, search_by)
        context["products"] = data["products"]
        context["content_title"] = data["content_title"]
        return context

    @staticmethod
    def search(request, kwargs, search_by, seller_id_in=[-1]):
        possible_search_by = ["all", "product_name", "active_substance", "excipient", "illness"]

        if search_by not in possible_search_by:
            raise Http404()

        cursor = connection.cursor()
        search_query = request.GET.get('query')
        print(search_by)
        print(search_query)
        print("....")

        if Utilities.as_seller(kwargs):
            if Utilities.is_pharmacist(request) or Utilities.is_pharmaceutical_company(request):
                cursor.execute("""
                                        select products.id, products.has_sponsor, products.name, products.slug,images.file, x.min_price as price
                                        from products join
                                             images on images.product_id = products.id join
                                             packages on packages.product_id = products.id join
                                             (select product_id, min(price) as min_price from packages group by product_id) as x
                                             on x.product_id = products.id and price = x.min_price
                                        where images.is_main = true and packages.seller_id = %s order by has_sponsor desc;
                                """, [request.user.seller.id])
            else:
                raise PermissionDenied
        # acting as a customer
        else:
            if Utilities.is_pharmacist(request):
                # pharmacist can only buy from pharmaceutical company products that don't need prescription
                if search_by == "all":
                    cursor.execute("""
                                            select products.id, products.has_sponsor, products.name, products.slug,images.file, x.min_price as price
                                            from products join
                                                 images on images.product_id = products.id join
                                                 packages on packages.product_id = products.id
                                                 join (select product_id, min(price) as min_price from packages group by product_id) as x
                                                 on x.product_id = products.id and price = x.min_price

                                                 join sellers on packages.seller_id = sellers.id

                                            where images.is_main = true and packages.available_quantity > 0 and 
                                                  products.needs_prescription = false and sellers.is_pharmacist = false order by has_sponsor desc;
                                            """, )
                elif search_by == "product_name":
                    cursor.execute("""
                                            select products.id, products.has_sponsor, products.name, products.slug,images.file, x.min_price as price
                                            from products join
                                                 images on images.product_id = products.id join
                                                 packages on packages.product_id = products.id 
                                                 join (select product_id, min(price) as min_price from packages group by product_id) as x
                                                 on x.product_id = products.id and price = x.min_price
                                                 join sellers on packages.seller_id = sellers.id
                                            where images.is_main = true and packages.available_quantity > 0 and 
                                                  products.needs_prescription = false and sellers.is_pharmacist = false and 
                                                  products.name like %s order by has_sponsor desc;
                                            """, [f"%{search_query}%"])
                elif search_by == "active_substance":
                    cursor.execute("""
                                            select products.id, products.has_sponsor, products.name, products.slug,images.file, x.min_price as price
                                            from products join
                                                 images on images.product_id = products.id join
                                                 packages on packages.product_id = products.id
                                                 join activeSubstances on products.active_substance_id = activeSubstances.id
                                                 join (select product_id, min(price) as min_price from packages group by product_id) as x
                                                 on x.product_id = products.id and price = x.min_price
                                                 join sellers on packages.seller_id = sellers.id
                                            where images.is_main = true and packages.available_quantity > 0 and 
                                                  products.needs_prescription = false and sellers.is_pharmacist = false and 
                                                  activeSubstances.name like %s order by has_sponsor desc;
                                            """, [f"%{search_query}%"])
                elif search_by == "excipient":
                    cursor.execute("""
                                            select products.id, products.has_sponsor, products.name, products.slug,images.file, x.min_price as price
                                            from products join
                                                 images on images.product_id = products.id join
                                                 packages on packages.product_id = products.id
                                                 join products_excipients on products.id = products_excipients.product_id
                                                 join excipients on excipients.id = products_excipients.excipient_id 
                                                 join (select product_id, min(price) as min_price from packages group by product_id) as x
                                                 on x.product_id = products.id and price = x.min_price
                                                 join sellers on packages.seller_id = sellers.id
                                            where images.is_main = true and packages.available_quantity > 0 and 
                                                  products.needs_prescription = false and sellers.is_pharmacist = false and 
                                                  excipients.name like %s order by has_sponsor desc;
                                            """, [f"%{search_query}%"])
                elif search_by == "illness":
                    cursor.execute("""
                                            select products.id, products.has_sponsor, products.name, products.slug,images.file, x.min_price as price
                                            from products 
                                                 join images on images.product_id = products.id 
                                                 join packages on packages.product_id = products.id
                                                 join products_illnesses on products.id = products_illnesses.product_id
                                                 join illnesses on illnesses.id = products_illnesses.illness_id 
                                                 join (select product_id, min(price) as min_price from packages group by product_id) as x
                                                 on x.product_id = products.id and price = x.min_price
                                                 join sellers on packages.seller_id = sellers.id
                                            where images.is_main = true and packages.available_quantity > 0 and 
                                                  products.needs_prescription = false and sellers.is_pharmacist = false and 
                                                  illnesses.name like %s order by has_sponsor desc;
                                            """, [f"%{search_query}%"])

            elif Utilities.is_pharmaceutical_company(request):
                # pharmaceutical company can only buy from pharmacist products that need prescription
                if search_by == "all":
                    cursor.execute("""
                                            select products.id, products.has_sponsor, products.name, products.slug,images.file, x.min_price as price
                                            from products 
                                                 join images on images.product_id = products.id 
                                                 join packages on packages.product_id = products.id
                                                 join (select product_id, min(price) as min_price from packages group by product_id) as x
                                                 on x.product_id = products.id and price = x.min_price
                                                 join sellers on packages.seller_id = sellers.id
                                            where images.is_main = true and packages.available_quantity > 0 and 
                                                  products.needs_prescription = true and sellers.is_pharmacist = true order by has_sponsor desc;
                                            """, )
                elif search_by == "product_name":
                    cursor.execute("""
                                            select products.id, products.has_sponsor, products.name, products.slug,images.file, x.min_price as price
                                            from products 
                                                 join images on images.product_id = products.id 
                                                 join packages on packages.product_id = products.id
                                                 join (select product_id, min(price) as min_price from packages group by product_id) as x
                                                 on x.product_id = products.id and price = x.min_price
                                                 join sellers on packages.seller_id = sellers.id
                                            where images.is_main = true and packages.available_quantity > 0 and 
                                                  products.needs_prescription = true and sellers.is_pharmacist = true
                                                  and products.name like %s order by has_sponsor desc;
                                            """, [f"%{search_query}%"])
                elif search_by == "active_substance":
                    cursor.execute("""
                                            select products.id, products.has_sponsor, products.name, products.slug,images.file, x.min_price as price
                                            from products 
                                                 join images on images.product_id = products.id 
                                                 join packages on packages.product_id = products.id
                                                 join activeSubstances on products.active_substance_id = activeSubstances.id
                                                 join (select product_id, min(price) as min_price from packages group by product_id) as x
                                                 on x.product_id = products.id and price = x.min_price
                                                 join sellers on packages.seller_id = sellers.id
                                            where images.is_main = true and packages.available_quantity > 0 and 
                                                  products.needs_prescription = true and sellers.is_pharmacist = true
                                                  and activeSubstances.name like %s order by has_sponsor desc;
                                            """, [f"%{search_query}%"])
                elif search_by == "excipient":
                    cursor.execute("""
                                            select products.id, products.has_sponsor, products.name, products.slug,images.file, x.min_price as price
                                            from products 
                                                 join images on images.product_id = products.id 
                                                 join packages on packages.product_id = products.id
                                                 join products_excipients on products.id = products_excipients.product_id
                                                 join excipients on excipients.id = products_excipients.excipient_id 
                                                 join (select product_id, min(price) as min_price from packages group by product_id) as x
                                                 on x.product_id = products.id and price = x.min_price
                                                 join sellers on packages.seller_id = sellers.id
                                            where images.is_main = true and packages.available_quantity > 0 and 
                                                  products.needs_prescription = true and sellers.is_pharmacist = true
                                                  and excipients.name like %s order by has_sponsor desc;
                                            """, [f"%{search_query}%"])
                elif search_by == "illness":
                    cursor.execute("""
                                            select products.id, products.has_sponsor, products.name, products.slug,images.file, x.min_price as price
                                            from products 
                                                 join images on images.product_id = products.id 
                                                 join packages on packages.product_id = products.id
                                                 join products_illnesses on products.id = products_illnesses.product_id
                                                 join illnesses on illnesses.id = products_illnesses.illness_id
                                                 join (select product_id, min(price) as min_price from packages group by product_id) as x
                                                 on x.product_id = products.id and price = x.min_price
                                                 join sellers on packages.seller_id = sellers.id
                                            where images.is_main = true and packages.available_quantity > 0 and 
                                                  products.needs_prescription = true and sellers.is_pharmacist = true
                                                  and illnesses.name like %s order by has_sponsor desc;
                                            """, [f"%{search_query}%"])
            else:
                if search_by == "all":
                    cursor.execute(f"""
                                            select distinct products.id, products.has_sponsor, products.name, products.slug,images.file, x.min_price as price
                                            from products join
                                                 images on images.product_id = products.id join
                                                 packages on packages.product_id = products.id join
                                                 (select product_id, min(price) as min_price from packages group by product_id) as x
                                                 on x.product_id = products.id and price = x.min_price
                                            where images.is_main = true and packages.available_quantity > 0
                                            and packages.seller_id {"not" if seller_id_in[0] == -1 else ""} in %s order by has_sponsor desc;
                                            """, [seller_id_in])
                elif search_by == "product_name":
                    cursor.execute("""
                                            select distinct products.id, products.has_sponsor, products.name, products.slug,images.file, x.min_price as price
                                            from products
                                                 join images on images.product_id = products.id
                                                 join packages on packages.product_id = products.id
                                                 join (select product_id, min(price) as min_price from packages group by product_id) as x
                                                 on x.product_id = products.id and price = x.min_price
                                            where images.is_main = true and packages.available_quantity > 0 and products.name like %s order by has_sponsor desc;
                                            """, [f"%{search_query}%"])
                elif search_by == "active_substance":
                    cursor.execute("""
                                            select distinct products.id, products.has_sponsor, products.name, products.slug,images.file, x.min_price as price
                                            from products join
                                                 images on images.product_id = products.id
                                                 join packages on packages.product_id = products.id 
                                                 join activeSubstances on products.active_substance_id = activeSubstances.id
                                                 join (select product_id, min(price) as min_price from packages group by product_id) as x
                                                 on x.product_id = products.id and price = x.min_price
                                            where images.is_main = true and packages.available_quantity > 0 and activeSubstances.name like %s order by has_sponsor desc;
                                            """, [f"%{search_query}%"])
                elif search_by == "excipient":
                    cursor.execute("""
                                            select distinct products.id, products.has_sponsor, products.name, products.slug,images.file, x.min_price as price
                                            from products
                                                 join images on images.product_id = products.id 
                                                 join packages on packages.product_id = products.id 
                                                 join products_excipients on products.id = products_excipients.product_id
                                                 join excipients on excipients.id = products_excipients.excipient_id 
                                                 join (select product_id, min(price) as min_price from packages group by product_id) as x
                                                 on x.product_id = products.id and price = x.min_price
                                            where images.is_main = true and packages.available_quantity > 0 and excipients.name like %s order by has_sponsor desc;
                                            """, [f"%{search_query}%"])
                elif search_by == "illness":
                    cursor.execute("""
                                            select distinct products.id, products.has_sponsor, products.name, products.slug,images.file, x.min_price as price
                                            from products
                                                 join images on images.product_id = products.id 
                                                 join packages on packages.product_id = products.id 
                                                 join products_illnesses on products.id = products_illnesses.product_id
                                                 join illnesses on illnesses.id = products_illnesses.illness_id 
                                                 join (select product_id, min(price) as min_price from packages group by product_id) as x
                                                 on x.product_id = products.id and price = x.min_price
                                            where images.is_main = true and packages.available_quantity > 0 and illnesses.name like %s order by has_sponsor desc;
                                            """, [f"%{search_query}%"])

        products = Utilities.dict_fetchall(cursor)
        products = None if len(products) == 0 else products
        content_title = None
        if search_by == "all":
            content_title = "Prodotti"
        elif search_by == "product_name":
            content_title = f"Ricerca di {search_query}"
        elif search_by == "active_substance":
            content_title = f"Ricerca di tutti i prodotti con principio attivo: {search_query}"
        elif search_by == "excipient":
            content_title = f"Ricerca di tutti i prodotti con eccipiente: {search_query}"
        elif search_by == "illness":
            content_title = f"Ricerca di tutti i prodotti per curare: {search_query}"
        return {"products": products, "content_title": content_title}


@method_decorator(Utilities.CUSTOMER_AUTH_DECORATORS, name='dispatch')
class IndexProductsSellersView(TemplateView):

    def get_context_data(self, **kwargs):
        seller_id = kwargs["seller_id"]
        context = super().get_context_data()
        self.template_name = 'shop/customer/products/index.html'
        search_by = "all"
        data = IndexProductsView.search(self.request, kwargs, search_by, [seller_id])
        context["products"] = data["products"]
        seller = get_object_or_404(Seller, id=seller_id)
        context["content_title"] = f"Prodotti di {seller.user.username}"
        return context


@method_decorator(Utilities.SELLER_AUTH_TRANSACTION_DECORATORS, name='dispatch')
class CreateProductsPackagesSponsorshipsView(View):

    # check if package is already sponsored
    @staticmethod
    def check(request, kwargs):
        product_id = kwargs["product_id"]
        if Utilities.as_seller(kwargs):
            if Utilities.is_pharmacist(request) or Utilities.is_pharmaceutical_company(request):
                package_id = kwargs["package_id"]
                package_queryset = Package.objects.filter(id=package_id, product_id=product_id,
                                                          seller=request.user.seller)
                package = package_queryset.first()

                if package:
                    try:
                        already_sponsored_package = SponsoredPackage.objects.get(package_id=package_id)
                        return True, already_sponsored_package
                    except ObjectDoesNotExist:
                        return False, None
        return None, None

    def post(self, request, *args, **kwargs):
        is_package_already_sponsored, already_sponsored_package = CreateProductsPackagesSponsorshipsView.check(
            self.request, kwargs)
        product_id = kwargs["product_id"]
        package_id = kwargs["package_id"]

        if is_package_already_sponsored == False:
            SponsoredPackage.objects.create(package_id=package_id)
            Package.objects.filter(pk=package_id).update(is_sponsored=True)
            Product.objects.filter(pk=product_id).update(has_sponsor=True)

        return redirect(reverse_lazy('seller.products.show', kwargs={"pk": product_id}))


@method_decorator(Utilities.SELLER_AUTH_TRANSACTION_DECORATORS, name='dispatch')
class DestroyProductsPackagesSponsorshipsView(View):

    def post(self, request, *args, **kwargs):
        is_package_already_sponsored, already_sponsored_package = CreateProductsPackagesSponsorshipsView.check(self.request, kwargs)
        if is_package_already_sponsored == True:
            already_sponsored_package.delete()
            Package.objects.filter(pk=kwargs["package_id"]).update(is_sponsored=False)
            product_id = kwargs["product_id"]
            if not Package.objects.filter(Q(product_id=product_id) & Q(is_sponsored=True)):
                Product.objects.filter(pk=product_id).update(has_sponsor=False)

        return redirect(reverse_lazy('seller.products.show', kwargs={"pk": kwargs["product_id"]}))


@method_decorator(Utilities.CUSTOMER_AUTH_DECORATORS, name='dispatch')
class ShowProfilesView(DetailView):
    model = User

    def get_context_data(self, **kwargs):
        context = super(ShowProfilesView, self).get_context_data()
        user = context["user"]

        if Utilities.is_customer(self.request) and hasattr(user, Utilities.SELLER_TAG):
            self.template_name = "shop/customer/profiles/seller/show.html"
            seller = user.seller
            context["content_title"] = f"Profilo del venditore {user.username}"
            context["seller_type"] = "Farmacista" if user.seller.is_pharmacist else "Casa farmaceutica"
            context["feedbacks"] = Feedback.objects.filter(order__seller=seller)
            return context


@method_decorator(Utilities.CUSTOMER_AUTH_DECORATORS, name='dispatch')
class CreateOrdersFeedbacksView(View):

    def post(self, request, *args, **kwargs):
        order_id = kwargs["order_id"]
        stars = int(self.request.POST.get("stars"))

        if stars > 5 or stars < 0:
            return JsonResponse({'message': "Il numero di stelle deve essere compreso tra 0 e 5"}, status=403)

        comment = self.request.POST.get("comment")

        try:
            order = Order.objects.get(Q(pk=order_id) & Q(customer=request.user.customer))
            feedback = Feedback.objects.create(stars=stars, comment=comment, order=order)
            return JsonResponse({'message': "Feedback aggiunto!"})

        except ObjectDoesNotExist:
            return JsonResponse({'message': "L'ordine non esiste o non appartiene a questo cliente!"}, status=403)


class ExportOrdersDataView(View):

    def post(self, request, *args, **kwargs):
        if not Utilities.is_admin(request):
            orders = Order.objects.filter(customer=request.user.customer).values_list('id', 'date','total_price', 'total_vat_price','address__city','address__country','address__province')
            orders = list(orders)
            orders.insert(0, ('id', 'date','total_price', 'total_vat_price','address__city','address__country','address__province'))
        else:
            orders = Order.objects.all().values_list('id',
                                                     'date',
                                                     'total_price',
                                                     'total_vat_price',
                                                     'status_id',
                                                     'seller_id',
                                                     'seller__name',
                                                     'seller__surname',
                                                     'seller__business_name',
                                                     'seller__phone',
                                                     'seller__codice_fiscale',
                                                     'seller__vat_number',
                                                     'seller__is_pharmacist',
                                                     'seller__license_number',
                                                     'orders__address__city',
                                                     'orders__address__country',
                                                     'orders__address__province',
                                                     'orders__address__postal_code',
                                                     'orders__address__street',
                                                     'orders__address__further_info',
                                                     'orders__address__is_billing',
                                                     'orders__address__is_shipping'
                                                     )
            orders = list(orders)
            orders.insert(0, ('id',
                              'date',
                              'total_price',
                              'total_vat_price',
                              'status_id',
                              'seller_id',
                              'seller__name',
                              'seller__surname',
                              'seller__business_name',
                              'seller__phone',
                              'seller__codice_fiscale',
                              'seller__vat_number',
                              'seller__is_pharmacist',
                              'seller__license_number',
                              'orders__address__city',
                              'orders__address__country',
                              'orders__address__province',
                              'orders__address__postal_code',
                              'orders__address__street'
                              'orders__address__house_number',
                              'orders__address__further_info',
                              'orders__address__is_billing',
                              'orders__address__is_shipping'
                              ))
        return excel.make_response_from_array(orders, 'csv')



