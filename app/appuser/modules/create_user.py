from appauth.modules.google_auth import verify_google_token

from appuser.models.user import User


def create_user(token: str) -> None:
    id_info = verify_google_token(token)
    google_id = id_info.google_id
    if User.objects.filter(google_id=google_id).exists():
        return
    if not id_info.verified:
        raise ValueError("Google account is not verified.")
    User.objects.create(google_id=google_id, verified=id_info.verified)
