from uuid import UUID

from ninja import Field, Schema


class GetUserIn(Schema):
    google_auth_token: str = Field(
        ..., description="The Google authentication token obtained from the client after signing in with Google"
    )


class GetUserOut(Schema):
    id: UUID = Field(..., description="The unique identifier of the user")
    verified: bool = Field(..., description="Whether the user's email is verified with Google")
