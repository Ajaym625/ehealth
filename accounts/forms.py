from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User, Group
from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.utils.decorators import method_decorator

from classes.Utilities import Utilities
from shop.models import Cart, Coupon
from accounts.models import Customer, Address, Seller

from django.db import transaction


@method_decorator(transaction.atomic, name='save')
class CreateUserForm(UserCreationForm):

    user_group = forms.ChoiceField(label="Tipo di account",
                                   widget=forms.Select(attrs={'class': 'form-select mb-3 btn-outline-primary', 'id': 'user_group_data_floating'}),
                                   choices=Utilities.map_user_groups(exclude_groups_names=["admin"]))

    name = forms.CharField(label="Nome", max_length=100,
                           widget=forms.TextInput(attrs={'class': 'form-control mb-3 border-primary',
                                                         'placeholder': 'Nome'}))
    surname = forms.CharField(label="Cognome", max_length=100,
                              widget=forms.TextInput(attrs={'class': 'form-control mb-3 border-primary',
                                                            'placeholder': 'Cognome'}))
    phone = forms.CharField(label="Telefono", max_length=100,
                            widget=forms.TextInput(attrs={'class': 'form-control mb-3 border-primary',
                                                          'placeholder': 'Telefono'}))
    codice_fiscale = forms.CharField(label="Codice fiscale", max_length=16,
                                     widget=forms.TextInput(attrs={'class': 'form-control mb-3 border-primary',
                                                                   'placeholder': 'Codice fiscale'}))

    blockchain_address = forms.CharField(label="Indirizzo blockchain", max_length=42,
                                     widget=forms.TextInput(attrs={'class': 'form-control mb-3 border-primary',
                                                                   'placeholder': 'Indirizzo blockchain'}))

    business_name = forms.CharField(
        label = 'Ragione sociale',
        max_length=220,
        required=False,
        widget=forms.TextInput(
            attrs={'class': 'visually-hidden form-control mb-3 border-primary','placeholder': 'Ragione sociale'}
        )
    )

    vat_number = forms.CharField(
        label = 'Partita IVA',
        min_length=11,
        max_length=11,
        required=False,
        widget=forms.TextInput(
            attrs={'class': 'visually-hidden form-control mb-3 border-primary', 'placeholder': 'Partita IVA'}
        )
    )

    license_number = forms.CharField(
        label = 'Numero di licenza',
        max_length=10,
        required=False,
        widget=forms.TextInput(
            attrs={'class': 'visually-hidden form-control mb-3 border-primary', 'placeholder': 'Numero di licenza'}
        )
    )

    password1 = forms.CharField(label="Password", widget=forms.PasswordInput(attrs={'class': 'form-control mb-3 border-primary',
                                                                                    'placeholder': 'Password'}))

    password2 = forms.CharField(label="Conferma password",
                                widget=forms.PasswordInput(attrs={'class': 'form-control mb-3 border-primary',
                                                                  'placeholder': 'Conferma password'}))



    def save(self, commit=True):
        self.is_valid()
        user = super().save(commit)

        group = Group.objects.get(pk=self.cleaned_data["user_group"])
        user.groups.add(group)

        group_name = group.name
        seller = None
        customer = None
        if group_name == Utilities.CUSTOMER_GROUP_NAME:
            customer = Customer.objects.create(
                name=self.cleaned_data["name"],
                surname=self.cleaned_data["surname"],
                phone=self.cleaned_data["phone"],
                codice_fiscale=self.cleaned_data["codice_fiscale"],
                blockchain_address=self.cleaned_data["blockchain_address"],
                user=user,
            )

        elif group_name == Utilities.PHARMACEUTICAL_COMPANY_GROUP_NAME:
            seller = Seller.objects.create(
                name=self.cleaned_data["name"],
                surname=self.cleaned_data["surname"],
                phone=self.cleaned_data["phone"],
                codice_fiscale=self.cleaned_data["codice_fiscale"],
                business_name=self.cleaned_data["business_name"],
                vat_number=self.cleaned_data["vat_number"],
                blockchain_address=self.cleaned_data["blockchain_address"],
                user=user,
                approved=True
            )


        elif group_name == Utilities.PHARMACIST_GROUP_NAME:
            seller = Seller.objects.create(
                name=self.cleaned_data["name"],
                surname=self.cleaned_data["surname"],
                phone=self.cleaned_data["phone"],
                codice_fiscale=self.cleaned_data["codice_fiscale"],
                business_name=self.cleaned_data["business_name"],
                vat_number=self.cleaned_data["vat_number"],
                is_pharmacist=True,
                license_number=self.cleaned_data["license_number"],
                blockchain_address=self.cleaned_data["blockchain_address"],
                user=user
            )

            seller.save()

        if seller is not None:
            # creating customer account for the seller ( he can act as a customer too)
            customer = Customer.objects.create(
                name=seller.name,
                surname=seller.surname,
                phone=seller.phone,
                codice_fiscale=seller.codice_fiscale,
                user=user
            )

            # group to be added to sellers that can be also customers
            customer_group = Group.objects.get(name=Utilities.CUSTOMER_GROUP_NAME)
            user.groups.add(customer_group)

        if customer is not None:
            # create default cart for the customer,
            # checking if it already exists even if it's sure it doesn't as a multiple check
            try:
                customer_cart = customer.cart
            except ObjectDoesNotExist:
                Cart.objects.create(customer_id=customer.id)

        return user

    class Meta:
        model = User
        fields = ['username','email','password1','password2']

        labels = {
            "username": "Nome utente",
            "email": "Indirizzo email",

        }

        help_texts = {
            'username': None
        }

        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control mb-3 border-primary',
                                               'placeholder': labels['username'] }),
            'email': forms.TextInput(attrs={'class': 'form-control mb-3 border-primary',
                                            'placeholder': labels['email']}),

            # 'password confirmation': forms.TextInput(attrs={'class': 'form-control mb-3 border-primary',
            #                                                 'placeholder': labels['Password confirmation']}),
        }




class CreateAddressForm(forms.ModelForm):
    class Meta:
        model = Address
        exclude = ['is_shipping', 'customer']

        labels = {
            "street": "Via",
            "house_number": "Numero",
            "city": "Città",
            "province": "Provincia",
            "postal_code": "Codice postale",
            "country": "Regione",
            "further_info": "Ulteriori info per il corriere",
            "is_billing": "Usa anche come indirizzo di fatturazione",
        }
        error_messages = {

        }

        widgets = {
            'street': forms.TextInput(attrs={'class': 'form-control mb-3 border-primary',
                                             'placeholder': labels['street']}),
            'house_number': forms.TextInput(attrs={'class': 'form-control mb-3 border-primary',
                                                   'placeholder': labels['house_number']}),
            'city': forms.TextInput(attrs={'class': 'form-control mb-3 border-primary',
                                           'placeholder': labels['city']}),
            'province': forms.TextInput(attrs={'class': 'form-control mb-3 border-primary',
                                               'placeholder': labels['province']}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control mb-3 border-primary',
                                                  'placeholder': labels['postal_code']}),
            'country': forms.TextInput(attrs={'class': 'form-control mb-3 border-primary',
                                              'placeholder': labels['country']}),
            'further_info': forms.Textarea(attrs={'class': 'form-control mb-3 border-primary',
                                                  'placeholder': labels['further_info'], 'rows': 3}),
        }

    field_order = Meta.labels.keys()