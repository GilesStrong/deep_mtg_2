from typing import Callable

from beartype import beartype as _beartype
from django.conf import settings


def beartype(func: Callable) -> Callable:
    if settings.DISABLE_RUNTIME_TYPECHECKS:
        return func
    return _beartype(func)
