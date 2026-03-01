"""
URL configuration for app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from appai.api import router as ai_router
from appauth.api import router as auth_router
from appauth.modules.token import AccessTokenAuth
from appcards.api import router as cards_router
from appuser.api import router as user_router
from django.contrib import admin
from django.http import HttpRequest, HttpResponse
from django.urls import path
from ninja import NinjaAPI

app_api = NinjaAPI(auth=AccessTokenAuth())
app_api.add_router('/ai', ai_router)
app_api.add_router('/cards', cards_router)
app_api.add_router('/user', user_router)
app_api.add_router('/token', auth_router, auth=None)  # No auth for auth routes


def healthz(_request: HttpRequest) -> HttpResponse:
    return HttpResponse("ok", content_type="text/plain")


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/app/', app_api.urls),
    path('healthz', healthz),
]
