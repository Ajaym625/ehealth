from random import randint

from faker import Faker
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group

from accounts.models import Seller
from shop.models import Package, Product, Category, Image, Status


class Command(BaseCommand):
    help = "seed database for testing and development."

    def __init__(self):
        super().__init__()
        self.faker = Faker()

    def handle(self, *args, **options):
        print('seeding shop data...')
        Product.objects.all().delete()
        self.seed()
        print('done.')

    def seed(self):

        order_statuses = ["IN CORSO", "SPEDITO", "CANCELLATO", "RIMBORSATO"]

        for order_status in order_statuses:
            Status.objects.update_or_create(name=order_status)

        for i in range(10):
            Category.objects.create(name="category_" + self.faker.word() + "_" + str(self.faker.random_number(digits=3)))

        categories = Category.objects.all()
        sellers = Seller.objects.all()
        for i in range(100):
            aic = self.faker.random_number(digits=9)
            Product.objects.update_or_create(
                defaults={"name": self.faker.text(max_nb_chars=30),
                          "aic": aic,
                          "description": self.faker.text(max_nb_chars=200),
                          "active_substance": self.faker.word(),
                          "lot": self.faker.random_number(digits=5),
                          "category": categories[randint(0, len(categories) - 1)],
                          "seller": sellers[randint(0, len(sellers) - 1)]
                          },
                aic=aic
            )


        products = Product.objects.all()

        for product in products:
            for i in range(randint(2, 10)):
                image_url = self.faker.url(width=800, height=800)
                is_main = True if i == 0 else False
                image = Image.objects.create(
                    image_url=image_url,
                    is_main=is_main,
                    product=product
                )


        for i in range(500):
            price_without_vat = self.faker.pyfloat(left_digits=2, right_digits=2, max_value=56, positive=True)
            vat_percentage = 20
            vat_price = vat_percentage * price_without_vat/100
            price_with_vat = vat_price + price_without_vat

            types = ["bustine", "compresse"]
            Package.objects.create(
                **{
                    "type": types[randint(0, len(types) - 1)],
                    "amount": self.faker.random_number(digits=2),
                    "dosage": self.faker.random_number(digits=3),
                    "price": price_with_vat,
                    "vat_percentage": vat_percentage,
                    "vat_price": vat_price,
                    "available_quantity": self.faker.random_number(digits=2),
                    "product": products[randint(0, len(products) - 1)],

                }
            )




        category1 = Category.objects.update_or_create(
            defaults={"name": "medicinali"},
            name="medicinali"
        )

        category2 = Category.objects.update_or_create(
            defaults={"name": "Integratori"},
            name="Integratori"
        )

        category3 = Category.objects.update_or_create(
            defaults={"name": "Igiene per il corpo"},
            name="Igiene per il corpo"
        )

        product1 = Product.objects.update_or_create(
            defaults={"name": "Bioritmon Energy Defend Integratore Energetico",
                      "aic": "982005896",
                      "description": "Bioritmon Energy Defend è un integratore alimentare che favorisce il metabolismo energertico e supporta il normale funzionamento del sisstema immunitario.",
                      "active_substance": "",
                      "lot": 34,
                      "category": category1[0],
                      "seller": sellers[randint(0, len(sellers) - 1)],
                      },
            aic="982005896"
        )

        packages_kwargs =[
            {"type": "bustine",
             "amount": 14,
             "dosage": 500,
             "price": 12,
             "vat_percentage": 20,
             "vat_price": 2,
             "available_quantity": 20,
             "product": product1[0],
             },
            {"type": "bustine",
             "amount": 28,
             "dosage": 500,
             "price": 24,
             "available_quantity": 20,
             "vat_price": 4,
             "product": product1[0],
             },
        ]

        for package_kwargs in packages_kwargs:

            package = Package.objects.filter(**package_kwargs)
            if not package.count():
                Package.objects.create(**package_kwargs)


