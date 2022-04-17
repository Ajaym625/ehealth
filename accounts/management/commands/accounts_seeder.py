from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group

from classes.Utilities import Utilities


class Command(BaseCommand):
    help = "seed database for testing and development."

    def handle(self, *args, **options):
        print('seeding accounts data...')
        seed()
        print('done.')


def seed():
    admin_group, created = Group.objects.update_or_create(name=Utilities.ADMIN_GROUP_NAME)
    customer_group, created = Group.objects.update_or_create(name=Utilities.CUSTOMER_GROUP_NAME)
    seller_pharmaceutical_company_group, created = Group.objects.update_or_create(name=Utilities.PHARMACEUTICAL_COMPANY_GROUP_NAME)
    seller_pharmacist_group, created = Group.objects.update_or_create(name=Utilities.PHARMACIST_GROUP_NAME)



