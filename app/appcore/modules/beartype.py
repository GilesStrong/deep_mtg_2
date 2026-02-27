from typing import Callable, ParamSpec, TypeVar

from beartype import beartype as _beartype
from django.conf import settings

P = ParamSpec("P")
R = TypeVar("R")


def beartype(func: Callable[P, R]) -> Callable[P, R]:
    if settings.DISABLE_RUNTIME_TYPECHECKS:
        return func
    return _beartype(func)
