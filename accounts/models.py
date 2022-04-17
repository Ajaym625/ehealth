from django.db import models
from django.contrib.auth.models import User, Group

# Create your models here.
from shop.models import Order, Coupon


class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    surname = models.CharField(max_length=100)
    phone = models.CharField(max_length=100)
    codice_fiscale = models.CharField(max_length=16)
    chat_online = models.BooleanField(default=False)
    blockchain_address = models.CharField(max_length=42, default="")

    class Meta:
        db_table = "customers"


class Seller(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    surname = models.CharField(max_length=100)
    phone = models.CharField(max_length=100)
    codice_fiscale = models.CharField(max_length=16)
    business_name = models.CharField(max_length=220)  # ragione sociale
    vat_number = models.CharField(max_length=11)  # partita iva
    is_pharmacist = models.BooleanField(default=False)  # if False the seller is a private seller, else a pharmacist
    license_number = models.CharField(max_length=10, null=True)  # null if seller is not a pharmacist
    chat_online = models.BooleanField(default=False)
    approved = models.BooleanField(default=False)
    blockchain_address = models.CharField(max_length=42, default="")

    class Meta:
        db_table = "sellers"


class Address(models.Model):
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    province = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=5)
    street = models.CharField(max_length=100)
    house_number = models.IntegerField()
    further_info = models.TextField(null=True, blank=True, default=None)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="addresses")
    is_billing = models.BooleanField(default=False)
    is_shipping = models.BooleanField(default=True)

    def __str__(self):

        return f'{self.customer.name} {self.customer.surname}, {self.street} {self.house_number} {self.city} ({self.province}) {self.postal_code} - {self.country}'

    class Meta:
        db_table = "addresses"


