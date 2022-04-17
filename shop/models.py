from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


from classes.Utilities import Utilities


class Category(models.Model):
    name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=80, default=None)

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super(Category, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "categories"


class Excipient(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        db_table = "excipients"


class Illness(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        db_table = "illnesses"


# principio attivo
class ActiveSubstance(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        db_table = "activeSubstances"


# model for a generic medicine (product)
# https://www.aifa.gov.it/trova-farmaco
# https://www.zentiva.it/per-saperne-di-piu/salute-practica/educazione-alla-salute/come-si-leggono-le-confezioni-dei-farmaci#:~:text=Codice%20ATC%20(Anatomico%2C%20Terapeutico%2C,stesso%20codice%20ATC%20sono%20equivalenti.
class Product(models.Model):
    name = models.CharField(max_length=100)
    # https://www.fascicolosanitario.gov.it/it/sistemi-codifica-dati/informazioni/aic
    aic = models.CharField(max_length=9, null=True)
    description = models.TextField()
    active_substance = models.ForeignKey(ActiveSubstance, on_delete=models.CASCADE, related_name="products", default=None, blank=True, null=True)
    needs_prescription = models.BooleanField(default=False)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    slug = models.SlugField(max_length=160, default=None)
    excipients = models.ManyToManyField(Excipient, related_name="excipients_products", default=None)
    illnesses = models.ManyToManyField(Illness, related_name="illnesses_products",default=None)
    has_sponsor = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super(Product, self).save(*args, **kwargs)

    def __str__(self):
        return f'{self.name}'

    class Meta:
        db_table = "products"


# images related to each product
class Image(models.Model):
    file = models.FileField(null=False, default=None, upload_to="products")
    is_main = models.BooleanField(default=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")

    class Meta:
        db_table = "images"


# possible packages for the same medicine
class Package(models.Model):
    type = models.CharField(max_length=50)  # compresse/bustine/gocce
    amount = models.PositiveIntegerField()  # number of (type) in the package
    dosage = models.PositiveIntegerField()  # quantity in mg for each (type)
    price = models.DecimalField(max_digits=20, decimal_places=2)
    vat_percentage = models.DecimalField(max_digits=20, decimal_places=2, default=0)  # iva
    vat_price = models.DecimalField(max_digits=20, decimal_places=2, default=0)  # vat_price is already included in price
    available_quantity = models.IntegerField()
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="packages")
    seller = models.ForeignKey("accounts.Seller", on_delete=models.CASCADE, related_name="packages", default=None)
    is_sponsored = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.amount} {self.type} - {self.dosage} mg'

    class Meta:
        db_table = "packages"


class SponsoredPackage(models.Model):
    package = models.OneToOneField(Package, on_delete=models.CASCADE, related_name="sponsored_package")
    sponsorship_fee_percentage = models.DecimalField(max_digits=20, decimal_places=2,
                                                     default=Utilities.PACKAGE_SPONSORSHIP_FEE_PERCENTAGE)

    class Meta:
        db_table = "sponsoredPackages"



# order statuses
class Status(models.Model):
    name = models.CharField(max_length=50)

    class Meta:
        db_table = "statuses"


class Order(models.Model):
    date = models.DateTimeField(default=timezone.now)
    total_price = models.DecimalField(max_digits=20, decimal_places=2)
    total_vat_price = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    customer = models.ForeignKey("accounts.Customer", on_delete=models.CASCADE, related_name="orders")
    seller = models.ForeignKey("accounts.Seller", on_delete=models.CASCADE, related_name="orders", default=None, null=True)
    address = models.ManyToManyField("accounts.Address", through='OrderAddress',  related_name="addresses_orders")
    package = models.ManyToManyField(Package, through='PackageOrder', related_name="packages_orders")
    status = models.ForeignKey(Status, on_delete=models.SET_NULL, related_name="orders", null=True)
    # help_desk_coupon = models.TextField(default=None, null=True)
    class Meta:
        db_table = "orders"


class Coupon(models.Model):
    code = models.TextField(null=True, default=None)
    is_discounted = models.BooleanField(default=False)
    discount_percentage = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    fee_percentage = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    chat = models.OneToOneField("chat.Chat", on_delete=models.CASCADE, related_name="coupon", default=None)
    usable = models.BooleanField(default=False)

    class Meta:
        db_table = "coupons"


class Courier(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(null=True)
    standard_cost = models.DecimalField(max_digits=20, decimal_places=2)
    website_url = models.CharField(max_length=2048, null=True)

    class Meta:
        db_table = "couriers"


class Shipment(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="shipment")
    courier = models.ForeignKey(Courier, on_delete=models.CASCADE, related_name="courier")
    cost = models.DecimalField(max_digits=20, decimal_places=2)
    tracking_code = models.CharField(max_length=50, null=True)

    class Meta:
        db_table = "shipments"


class Cart(models.Model):
    package = models.ManyToManyField(Package, through='PackageCart', related_name="packages_carts")
    customer = models.OneToOneField("accounts.Customer", on_delete=models.CASCADE, related_name="cart", default=None)

    class Meta:
        db_table = "carts"


# many to many intermediate table between order and address
class OrderAddress(models.Model):
    address = models.ForeignKey("accounts.Address", on_delete=models.CASCADE, default=None, related_name="addresses")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, default=None, related_name="orders")
    raw_address = models.TextField()
    further_info = models.TextField(null=True, blank=True, default=None)
    is_shipping = models.BooleanField()
    is_billing = models.BooleanField()

    class Meta:
        db_table = "orders_addresses"


# many to many intermediate table between package and cart
class PackageCart(models.Model):
    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name="packages_carts_packages")
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="packages_carts_carts")
    requested_quantity = models.PositiveIntegerField()

    class Meta:
        db_table = "packages_carts"


# many to many intermediate table between package and order
class PackageOrder(models.Model):
    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name="packages_orders_packages")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="packages_orders_orders")
    requested_quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    vat_percentage = models.DecimalField(max_digits=20, decimal_places=2, default=0)  # iva
    vat_price = models.DecimalField(max_digits=20, decimal_places=2, default=0)  # vat_price is already included in price
    is_sponsored = models.BooleanField(default=False)
    sponsorship_cost = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    is_discounted = models.BooleanField(default=False)
    coupon = models.TextField(null=True, default=None)
    coupon_cost = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    discount_percentage = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    class Meta:
        db_table = "packages_orders"


class Feedback(models.Model):
    stars = models.IntegerField()
    comment = models.TextField(null=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="feedbacks", default=None)

    class Meta:
        db_table = "feedbacks"
