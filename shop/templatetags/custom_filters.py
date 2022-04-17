from django import template
from django.urls import resolve

from classes.Utilities import Utilities

register = template.Library()


@register.filter()
def __range__(min=1):
    return range(min)


@register.filter
def multiply(value, arg):
    return value * arg


@register.filter
def as_seller(kwargs):
    return Utilities.as_seller(kwargs)

@register.simple_tag(takes_context=True)
def is_active_route(context, route_name):
    request = context.get('request')
    return route_name == resolve(request.path_info).url_name
    # for view_name in view_names:
    #     if getattr(request.resolver_match, 'view_name', False) and request.resolver_match.view_name == view_name:
    #         return True
    # return ''


@register.simple_tag(takes_context=True)
def is_user_group(context, group_name):
    request = context.get('request')
    return request.user.groups.filter(name__in=[group_name]).count()
