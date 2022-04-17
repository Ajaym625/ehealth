from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import ListView, FormView, DetailView
from django.views.generic.base import TemplateView, RedirectView, View
from accounts.models import Address
from classes.Utilities import Utilities
from .auth_decorators import unauthenticated_user, ajax_login_required
from .forms import CreateUserForm, CreateAddressForm


@method_decorator(unauthenticated_user, name='dispatch')
class RegisterView(FormView):
    form_class = CreateUserForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        form.save()
        messages.success(self.request, f'Account creato per {form.cleaned_data.get("username")}')
        return redirect('login')


@method_decorator(unauthenticated_user, name='dispatch')
class LoginView(TemplateView):
    template_name = 'accounts/login.html'
    success_url = reverse_lazy('home')

    def post(self, request):

        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if hasattr(user, 'seller'):

                if user.seller.is_pharmacist and not user.seller.approved:
                    messages.info(request, "Il tuo account non è ancora approvato dal Servizio Sanitario Nazionale")
                    return self.get(request)

            login(request, user)
            try:
                return redirect(request.POST.get('next'))
            except:
                return redirect(self.success_url)
        else:
            messages.info(request, "Username o password non sono corretti")
            return self.get(request)


@method_decorator(ajax_login_required, name='dispatch')
class LogoutView(RedirectView):
    pattern_name = 'home'

    def get_redirect_url(self, *args, **kwargs):
        logout(self.request)
        return super(LogoutView, self).get_redirect_url()


class HomeView(RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        if Utilities.is_seller(self.request):
            return reverse_lazy('seller.dashboard')
        elif Utilities.is_admin(self.request):
            return reverse_lazy('administration.orders.index')
        else:
            return reverse_lazy('products.index')


# views related to addresses

@method_decorator(Utilities.CUSTOMER_AUTH_DECORATORS, name='dispatch')
class IndexAddressesView(ListView):
    template_name = 'accounts/addresses/index.html'
    model = Address
    context_object_name = 'addresses'

    def get_queryset(self):
        base_query = super().get_queryset()
        addresses = base_query.filter(customer=self.request.user.customer)
        return addresses if addresses.count() > 0 else None

    def render_to_response(self, context, **response_kwargs):
        if context["addresses"] is None:
            return redirect('addresses.create')

        context["content_title"] = "I tuoi indirizzi"
        return super(IndexAddressesView, self).render_to_response(context)


@method_decorator(Utilities.CUSTOMER_AUTH_TRANSACTION_DECORATORS, name='dispatch')
class CreateAddressesView(FormView):
    form_class = CreateAddressForm
    template_name = 'accounts/addresses/create.html'
    success_url = reverse_lazy('addresses.index')

    def get_context_data(self, **kwargs):
        context = super(CreateAddressesView, self).get_context_data()
        # used to check if an address is going to be added after being redirected by an order page or not
        context['next'] = ''
        if 'next' in self.request.session:
            context['next'] = self.request.session['next']
            self.request.session.pop('next')
        return context

    def form_valid(self, form):
        customer = self.request.user.customer
        address = form.save(commit=False)
        address.customer = customer
        form.save()

        next_path = self.request.GET.get('next')
        if next_path != "":
            return redirect(next_path)

        return super(CreateAddressesView, self).form_valid(form)


@method_decorator(Utilities.CUSTOMER_AUTH_TRANSACTION_DECORATORS, name='dispatch')
class DestroyAddressesView(View):

    def post(self, request, *args, **kwargs):
        address = get_object_or_404(Address, Q(pk=kwargs["address_id"]) & Q(customer_id=self.request.user.customer.id))
        address.delete()
        return redirect('addresses.index')


