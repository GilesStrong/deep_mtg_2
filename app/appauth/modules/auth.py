from typing import Any, cast

from appuser.models.user import User
from django.http import HttpRequest


def get_user_from_request(request: HttpRequest) -> User:
    """
    Retrieves the authenticated user from an HTTP request object.

    Args:
        request (HttpRequest): The HTTP request object containing authentication information.

    Returns:
        User: The authenticated user extracted from the request's auth attribute.
    """
    try:
        return cast(Any, request).auth
    except AttributeError:
        raise ValueError("Request object does not have an 'auth' attribute or it is not set.")
