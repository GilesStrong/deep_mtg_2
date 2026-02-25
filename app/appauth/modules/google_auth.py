from app.app_settings import APP_SETTINGS
from google.auth.transport import requests
from google.oauth2 import id_token
from pydantic import BaseModel, ConfigDict, Field


class GoogleTokenVerificationResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    verified: bool = Field(..., description="Indicates whether the Google token is valid and verified.")
    google_id: str = Field(..., description="The unique identifier of the user from Google if the token is valid.")


def verify_google_token(token: str) -> GoogleTokenVerificationResult:
    """
    Verifies the authenticity of a Google OAuth2 token.

    This function validates the provided Google token using the Google OAuth2
    verification process and checks that the token was issued by Google's
    authentication servers.

    Args:
        token (str): The Google OAuth2 ID token string to be verified.

    Returns:
        GoogleTokenVerificationResult: An object containing the verification result and Google ID.

    Raises:
        ValueError: If the token issuer is not 'accounts.google.com' or
                    'https://accounts.google.com'.
        google.auth.exceptions.GoogleAuthError: If the token is invalid, expired,
                                                or cannot be verified against the
                                                Google Client ID.
    """
    idinfo = id_token.verify_oauth2_token(
        token,
        requests.Request(),
        APP_SETTINGS.GOOGLE_CLIENT_ID,
    )

    if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
        raise ValueError("Wrong issuer.")

    return GoogleTokenVerificationResult(verified=idinfo.get('email_verified', False), google_id=idinfo['sub'])
