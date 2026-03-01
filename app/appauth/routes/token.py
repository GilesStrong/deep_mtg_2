from app.app_settings import APP_SETTINGS
from appuser.models import User
from django.http import HttpRequest
from ninja import Router
from ninja.errors import HttpError

from appauth.models.token import RefreshToken
from appauth.modules.auth_rate_limit import check_auth_rate_limit
from appauth.modules.google_auth import verify_google_token
from appauth.modules.token import mint_access_token
from appauth.serializers.token import ExchangeIn, ExchangeOut, RefreshIn

router = Router(tags=["auth"])


@router.post(
    "/exchange",
    response=ExchangeOut,
    summary="Exchange Google ID token for access and refresh tokens",
    description="Exchange a Google ID token for an access token and a refresh token. The access token can be used to authenticate API requests, while the refresh token can be used to obtain new access tokens when the current one expires.",
    operation_id="exchange_google_token",
)
def exchange(request: HttpRequest, payload: ExchangeIn) -> ExchangeOut:
    """
    Exchange a Google ID token for access and refresh tokens.

    Validates the provided Google ID token, performs rate limiting, and returns
    a new access token and refresh token pair for the authenticated user.

    Args:
        request (HttpRequest): The incoming HTTP request object, used for rate
            limiting and extracting client metadata (User-Agent, IP address).
        payload (ExchangeIn): The request payload containing the Google ID token
            to be exchanged.

    Returns:
        ExchangeOut: An object containing the newly minted access token and
            refresh token.

    Raises:
        HttpError(429): If the rate limit for token exchange attempts is exceeded.
            The response includes the number of seconds to wait before retrying.
        HttpError(401): If the Google ID token is invalid or the associated email
            address has not been verified.
        HttpError(403): If the user's account has been blocked due to exceeding
            the maximum number of allowed policy violations
            (`APP_SETTINGS.N_WARNINGS_BEFORE_BLOCK`).

    Notes:
        - If no user exists with the given Google ID, a new user account is
          automatically created.
        - The refresh token is associated with the client's User-Agent and IP
          address for security tracking purposes.
    """
    rate_limit = check_auth_rate_limit(
        request,
        action="exchange",
        limit=APP_SETTINGS.AUTH_EXCHANGE_PER_MINUTE,
    )
    if not rate_limit.allowed:
        raise HttpError(429, f"Too many token exchange attempts. Retry in {rate_limit.retry_after_seconds}s")

    ident = verify_google_token(payload.google_id_token)

    if not ident.verified:
        raise HttpError(401, "Email not verified")

    user, _created = User.objects.get_or_create(
        google_id=ident.google_id,
        defaults={"verified": ident.verified},
    )
    if user.warning_count >= APP_SETTINGS.N_WARNINGS_BEFORE_BLOCK:
        raise HttpError(
            403,
            "Your account has been blocked due to multiple policy violations. Please contact support for assistance.",
        )

    access = mint_access_token(user_id=user.id)
    _rt, raw_refresh_token = RefreshToken.mint(
        user,
        user_agent=request.headers.get("User-Agent", ""),
        ip=request.META.get("REMOTE_ADDR"),
    )
    return ExchangeOut(access_token=access, refresh_token=raw_refresh_token)


@router.post(
    "/refresh",
    response=ExchangeOut,
    summary="Refresh access token using refresh token",
    description="Use a valid refresh token to obtain a new access token. This endpoint will also rotate the refresh token, invalidating the old one and issuing a new one.",
    operation_id="refresh_access_token",
)
def refresh(request: HttpRequest, payload: RefreshIn) -> ExchangeOut:
    """
    Refresh an access token using a valid refresh token.

    This endpoint implements refresh token rotation: upon successful validation,
    the provided refresh token is immediately revoked and a new refresh token is
    issued alongside a fresh access token.

    Args:
        request (HttpRequest): The incoming HTTP request object, used for rate
            limiting, IP address extraction, and User-Agent header retrieval.
        payload (RefreshIn): Request body containing the refresh token to be
            exchanged.

    Returns:
        ExchangeOut: A response object containing:
            - access_token (str): A newly minted JWT access token.
            - refresh_token (str): A newly issued raw refresh token, replacing
              the one that was consumed during this request.

    Raises:
        HttpError(429): If the caller has exceeded the allowed number of refresh
            attempts per minute (``AUTH_REFRESH_PER_MINUTE``). The response
            includes a ``retry_after_seconds`` hint.
        HttpError(401): If the provided refresh token does not exist in the
            database (``"Invalid refresh token"``).
        HttpError(401): If the provided refresh token has expired or has already
            been revoked (``"Refresh token expired or revoked"``).

    Notes:
        - Refresh token rotation ensures that each refresh token can only be used
          once, mitigating replay attacks.
        - The old refresh token's ``revoked_at`` timestamp is set to the current
          time before the new token pair is minted.
        - Rate limiting is enforced per request via ``check_auth_rate_limit``.
    """
    rate_limit = check_auth_rate_limit(
        request,
        action="refresh",
        limit=APP_SETTINGS.AUTH_REFRESH_PER_MINUTE,
    )
    if not rate_limit.allowed:
        raise HttpError(429, f"Too many token refresh attempts. Retry in {rate_limit.retry_after_seconds}s")

    try:
        rt = RefreshToken.from_raw_token(payload.refresh_token)
    except RefreshToken.DoesNotExist:
        raise HttpError(401, "Invalid refresh token")

    if not rt.is_valid():
        raise HttpError(401, "Refresh token expired or revoked")

    # Rotate the refresh token by revoking the old one and minting a new one
    rt.revoked_at = __import__("django.utils.timezone").utils.timezone.now()
    rt.save(update_fields=["revoked_at"])

    _new_rt, new_raw_refresh_token = RefreshToken.mint(
        rt.user,
        user_agent=request.headers.get("User-Agent", ""),
        ip=request.META.get("REMOTE_ADDR"),
    )

    access = mint_access_token(user_id=rt.user.id)
    return ExchangeOut(access_token=access, refresh_token=new_raw_refresh_token)
