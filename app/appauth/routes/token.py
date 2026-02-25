from appuser.models import User
from django.http import HttpRequest
from ninja import Router
from ninja.errors import HttpError

from appauth.models.token import RefreshToken
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
    ident = verify_google_token(payload.google_id_token)

    if not ident.verified:
        raise HttpError(401, "Email not verified")

    user, _created = User.objects.get_or_create(
        google_id=ident.google_id,
        defaults={"verified": ident.verified},
    )

    access = mint_access_token(user_id=user.id)
    rt = RefreshToken.mint(
        user,
        user_agent=request.headers.get("User-Agent", ""),
        ip=request.META.get("REMOTE_ADDR"),
    )
    return ExchangeOut(access_token=access, refresh_token=rt.token)


@router.post(
    "/refresh",
    response=ExchangeOut,
    summary="Refresh access token using refresh token",
    description="Use a valid refresh token to obtain a new access token. This endpoint will also rotate the refresh token, invalidating the old one and issuing a new one.",
    operation_id="refresh_access_token",
)
def refresh(request: HttpRequest, payload: RefreshIn) -> ExchangeOut:
    try:
        rt = RefreshToken.objects.select_related("user").get(token=payload.refresh_token)
    except RefreshToken.DoesNotExist:
        raise HttpError(401, "Invalid refresh token")

    if not rt.is_valid():
        raise HttpError(401, "Refresh token expired or revoked")

    # Rotate the refresh token by revoking the old one and minting a new one
    rt.revoked_at = __import__("django.utils.timezone").utils.timezone.now()
    rt.save(update_fields=["revoked_at"])

    new_rt = RefreshToken.mint(
        rt.user,
        user_agent=request.headers.get("User-Agent", ""),
        ip=request.META.get("REMOTE_ADDR"),
    )

    access = mint_access_token(user_id=rt.user.id)
    return ExchangeOut(access_token=access, refresh_token=new_rt.token)
