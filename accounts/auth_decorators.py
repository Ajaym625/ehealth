from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy, resolve

# checks if a logged user tries to access pages available only to unauthenticated users such as login or register page
import chat.models



def unauthenticated_user(view_func):
    def wrapper_func(request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("home")
        else:
            return view_func(request, *args, **kwargs)

    return wrapper_func


def allowed_users(allowed_roles=[]):

    def decorator(view_function):
        def wrapper_function(request, *args, **kwargs):

            if request.user.groups.filter(name__in=allowed_roles):
                return view_function(request, *args, **kwargs)
            else:
                raise PermissionDenied

        return wrapper_function

    return decorator


def ajax_login_required(view_func):
    def wrapper_func(request, *args, **kwargs):
        if not request.user.is_authenticated:
            url = f"{reverse_lazy('login')}?next={request.get_full_path()}"
            if request.is_ajax():
                return JsonResponse({"redirect": reverse_lazy('login')}, status=302)
            else:
                return redirect(url)
        else:
            # if not request.is_ajax():
            #     current_route_name = resolve(request.path_info).url_name
            #     not_evaluated_chats = chat.models.Chat.objects.filter(Q(ended=False) & Q(sender_id=request.user.id))
            #     if not_evaluated_chats:
            #         if current_route_name != "chats.index" and current_route_name != "chats.evaluate" :
            #             return redirect(reverse_lazy('chats.evaluate'))
            return view_func(request, *args, **kwargs)

    return wrapper_func
