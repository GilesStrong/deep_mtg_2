from django.http import HttpRequest
from ninja import Router
from ninja.errors import HttpError

from appuser.models.user import User
from appuser.modules.create_user import create_user
from appuser.modules.google_auth import verify_google_token
from appuser.serializers.user import GetUserIn, GetUserOut

router = Router(tags=['user'])


@router.get(
    '/',
    summary='Get user info',
    description='Retrieve information about the currently authenticated user.',
    response={200: GetUserOut},
    operation_id='get_user_info',
)
def get_user_info(request: HttpRequest, query_params: GetUserIn) -> GetUserOut:
    """
    Retrieve user information based on a Google authentication token.

    If the user does not exist in the database, a new user will be created.

    Args:
        request (HttpRequest): The HTTP request object (unused).
        query_params (GetUserIn): The query parameters containing the Google authentication token.
            - google_auth_token (str): A valid Google OAuth2 authentication token.

    Returns:
        GetUserOut: An object containing the user's information.
            - id (int): The user's database ID.
            - google_id (str): The user's Google ID.
            - verified (bool): Whether the user has been verified.

    Raises:
        HttpError (400): If the Google authentication token is invalid or cannot be verified.
        HttpError (400): If the Google account's email is not verified.
    """
    try:
        id_info = verify_google_token(query_params.google_auth_token)
    except ValueError:
        raise HttpError(400, "Invalid Google authentication token, or unable to verify token")

    google_id = id_info.google_id
    if not id_info.verified:
        raise HttpError(400, "Google account is not verified.")
    if not User.objects.filter(google_id=google_id).exists():
        create_user(query_params.google_auth_token)
    user = User.objects.get(google_id=google_id)
    return GetUserOut(id=user.id, verified=user.verified)
