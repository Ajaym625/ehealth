from random import randint

from django.contrib.auth.models import Group, User
from django.db import transaction
from django.db.models import Q
from accounts.auth_decorators import allowed_users, ajax_login_required


class Utilities:
    PHARMACIST_GROUP_NAME = "seller_pharmacist"
    PHARMACEUTICAL_COMPANY_GROUP_NAME = "seller_pharmaceutical_company"
    CUSTOMER_GROUP_NAME = "customer"
    ADMIN_GROUP_NAME = "admin"
    SELLER_GROUPS = [PHARMACIST_GROUP_NAME, PHARMACEUTICAL_COMPANY_GROUP_NAME, ADMIN_GROUP_NAME]
    CUSTOMER_AUTH_DECORATORS = [ajax_login_required, allowed_users([CUSTOMER_GROUP_NAME])]
    CUSTOMER_AUTH_TRANSACTION_DECORATORS = [ajax_login_required, allowed_users([CUSTOMER_GROUP_NAME]), transaction.atomic]
    SELLER_AUTH_DECORATORS = [ajax_login_required, allowed_users(SELLER_GROUPS)]
    ADMIN_AUTH_DECORATORS = [ajax_login_required, allowed_users([ADMIN_GROUP_NAME])]
    customer_auth_transactions_decorators = [ajax_login_required, allowed_users([CUSTOMER_GROUP_NAME]), transaction.atomic]
    SELLER_AUTH_TRANSACTION_DECORATORS = [ajax_login_required, allowed_users(SELLER_GROUPS), transaction.atomic]
    CUSTOMER_SELLER_AUTH_DECORATORS = [ajax_login_required, allowed_users([CUSTOMER_GROUP_NAME, PHARMACIST_GROUP_NAME, PHARMACEUTICAL_COMPANY_GROUP_NAME])]
    AUTH_DECORATORS = [ajax_login_required, allowed_users([CUSTOMER_GROUP_NAME, PHARMACIST_GROUP_NAME, PHARMACEUTICAL_COMPANY_GROUP_NAME, ADMIN_GROUP_NAME])]
    CUSTOMER_SELLER_AUTH_TRANSACTION_DECORATORS = [ajax_login_required, transaction.atomic, allowed_users([CUSTOMER_GROUP_NAME, PHARMACIST_GROUP_NAME, PHARMACEUTICAL_COMPANY_GROUP_NAME])]
    CUSTOMER_SELLER_ADMIN_AUTH_TRANSACTION_DECORATORS = [ajax_login_required, transaction.atomic, allowed_users([CUSTOMER_GROUP_NAME, PHARMACIST_GROUP_NAME, PHARMACEUTICAL_COMPANY_GROUP_NAME, ADMIN_GROUP_NAME])]
    CUSTOMER_TAG = "customer"
    SELLER_TAG = "seller"
    PACKAGE_SPONSORSHIP_FEE_PERCENTAGE = 10

    # https://docs.djangoproject.com/en/3.2/topics/db/sql/
    @staticmethod
    def dict_fetchall(cursor):
        # Return all rows from a cursor as a dict
        columns = [col[0] for col in cursor.description]
        return [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]

    @staticmethod
    def is_user_group(request, group_name):
        return hasattr(request.user, group_name)

    @staticmethod
    def is_customer(request):
        return Utilities.is_user_group(request, Utilities.CUSTOMER_TAG)

    @staticmethod
    def is_seller(request):
        return Utilities.is_user_group(request, Utilities.SELLER_TAG)

    @staticmethod
    def is_admin(request):
        return request.user.groups.filter(name__in=[Utilities.ADMIN_GROUP_NAME])

    # a seller has the same account to be used either as seller or as customer
    # checks if he is in seller or customer mode
    @staticmethod
    def as_seller(kwargs):
        if kwargs is not None:
            if "seller" in kwargs:
                return kwargs["seller"]

        return False

    @staticmethod
    def is_pharmacist(request):
        return Utilities.is_seller(request) and User.objects.filter(Q(id=request.user.id) &
                                                                    Q(groups__name__in=[Utilities.PHARMACIST_GROUP_NAME]) &
                                                                    Q(seller__is_pharmacist=True)).count()

    @staticmethod
    def is_pharmaceutical_company(request):
        return Utilities.is_seller(request) and User.objects.filter(Q(id=request.user.id) &
                                                                    Q(groups__name__in=[Utilities.PHARMACEUTICAL_COMPANY_GROUP_NAME]) &
                                                                    Q(seller__is_pharmacist=False)).count()
    @staticmethod
    def generate_help_desk_coupon(key):
        upper_alpha = "ABCDEFGHJKLMNPQRSTVWXYZ"
        upper_alpha_len = len(upper_alpha)
        random_string = "".join(upper_alpha[randint(0, upper_alpha_len - 1)] for i in range(8))
        return random_string + str(key)

    @staticmethod
    def map_user_groups(exclude_groups_names=[]):
        groups = list(Group.objects.filter(~Q(name__in=exclude_groups_names)).values_list('id','name'))
        mapped_groups = []

        for group in groups:
            group_id = group[0]
            name = group[1]

            if name == "seller_pharmaceutical_company":
                name = "Casa farmaceutica"

            elif name == "seller_pharmacist":
                name = "Farmacista"

            elif name == "customer":
                name = "Cliente"

            mapped_groups.append((group_id,name))

        return mapped_groups
