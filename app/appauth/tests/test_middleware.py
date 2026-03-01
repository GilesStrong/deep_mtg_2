from __future__ import annotations

from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from appauth.middleware import CookieAuthCSRFMiddleware


class CookieAuthCSRFMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = CookieAuthCSRFMiddleware(lambda _request: HttpResponse("ok", status=200))

    def test_allows_safe_method_without_csrf(self):
        """
        GIVEN a GET (safe) request with no CSRF header or cookies
        WHEN the middleware processes the request
        THEN it passes through and returns 200
        """
        request = self.factory.get("/api/app/cards/deck/")

        response = self.middleware(request)

        self.assertEqual(response.status_code, 200)

    def test_allows_unsafe_method_with_bearer_header(self):
        """
        GIVEN a POST request authenticated via a Bearer token in the Authorization header
        WHEN the middleware processes the request
        THEN it bypasses CSRF enforcement and returns 200
        """
        request = self.factory.post("/api/app/ai/deck/", data="{}", content_type="application/json")
        request.META["HTTP_AUTHORIZATION"] = "Bearer abc123"

        response = self.middleware(request)

        self.assertEqual(response.status_code, 200)

    def test_allows_unsafe_method_without_access_cookie(self):
        """
        GIVEN a POST request with no access cookie and no Authorization header
        WHEN the middleware processes the request
        THEN it passes through (no cookie-based auth to protect) and returns 200
        """
        request = self.factory.post("/api/app/ai/deck/", data="{}", content_type="application/json")

        response = self.middleware(request)

        self.assertEqual(response.status_code, 200)

    def test_blocks_cookie_auth_unsafe_method_when_csrf_header_missing(self):
        """
        GIVEN a POST request using cookie-based auth but no X-Backend-CSRF header
        WHEN the middleware processes the request
        THEN it rejects the request with 403
        """
        request = self.factory.post("/api/app/ai/deck/", data="{}", content_type="application/json")
        request.COOKIES["backend_access_token"] = "access-cookie"
        request.COOKIES["backend_csrf_token"] = "csrf-cookie"

        response = self.middleware(request)

        self.assertEqual(response.status_code, 403)

    def test_blocks_cookie_auth_unsafe_method_when_csrf_mismatch(self):
        """
        GIVEN a POST request using cookie-based auth with an X-Backend-CSRF header that does not match the CSRF cookie
        WHEN the middleware processes the request
        THEN it rejects the request with 403
        """
        request = self.factory.post("/api/app/ai/deck/", data="{}", content_type="application/json")
        request.COOKIES["backend_access_token"] = "access-cookie"
        request.COOKIES["backend_csrf_token"] = "csrf-cookie"
        request.META["HTTP_X_BACKEND_CSRF"] = "wrong-value"

        response = self.middleware(request)

        self.assertEqual(response.status_code, 403)

    def test_allows_cookie_auth_unsafe_method_when_csrf_matches(self):
        """
        GIVEN a POST request using cookie-based auth with an X-Backend-CSRF header that matches the CSRF cookie
        WHEN the middleware processes the request
        THEN it passes CSRF validation and returns 200
        """
        request = self.factory.post("/api/app/ai/deck/", data="{}", content_type="application/json")
        request.COOKIES["backend_access_token"] = "access-cookie"
        request.COOKIES["backend_csrf_token"] = "csrf-cookie"
        request.META["HTTP_X_BACKEND_CSRF"] = "csrf-cookie"

        response = self.middleware(request)

        self.assertEqual(response.status_code, 200)
