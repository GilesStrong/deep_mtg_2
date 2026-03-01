from uuid import UUID

from ninja import Field, Schema


class ExportDeckCardOut(Schema):
    card_id: UUID = Field(..., description='The unique ID of the card')
    card_name: str = Field(..., description='Card name')
    quantity: int = Field(..., description='Number of copies in this deck')


class ExportDeckOut(Schema):
    id: UUID = Field(..., description='The unique ID of the deck')
    name: str = Field(..., description='Deck name')
    short_summary: str | None = Field(None, description='Deck short summary')
    full_summary: str | None = Field(None, description='Deck full summary')
    set_codes: list[str] = Field(default_factory=list, description='Set codes represented in the deck')
    valid: bool = Field(..., description='Whether the deck currently passes validation checks')
    created_at: str = Field(..., description='Deck creation datetime in ISO 8601 format')
    updated_at: str = Field(..., description='Deck update datetime in ISO 8601 format')
    cards: list[ExportDeckCardOut] = Field(default_factory=list, description='Cards and quantities in this deck')


class ExportRefreshTokenOut(Schema):
    created_at: str = Field(..., description='Token creation datetime in ISO 8601 format')
    expires_at: str = Field(..., description='Token expiry datetime in ISO 8601 format')
    revoked_at: str | None = Field(None, description='Token revocation datetime in ISO 8601 format')
    user_agent: str = Field(..., description='User agent seen when token was minted')
    ip: str | None = Field(None, description='IP address seen when token was minted')


class ExportUserOut(Schema):
    id: UUID = Field(..., description='The unique ID of the user account')
    google_id: str = Field(..., description='Google account ID associated with this user')
    verified: bool = Field(..., description='Whether the user has a verified account')
    warning_count: int = Field(..., description='Number of policy warnings associated with this user')


class ExportDataOut(Schema):
    exported_at: str = Field(..., description='Export generation datetime in ISO 8601 format')
    user: ExportUserOut = Field(..., description='The user profile data')
    decks: list[ExportDeckOut] = Field(default_factory=list, description='All decks owned by the user')
    refresh_tokens: list[ExportRefreshTokenOut] = Field(
        default_factory=list,
        description='Refresh token metadata associated with this user',
    )


class DeleteAccountRequestOut(Schema):
    confirmation_token: str = Field(..., description='Short-lived token required to confirm account deletion')
    expires_in_seconds: int = Field(..., description='Number of seconds before the confirmation token expires')


class DeleteAccountIn(Schema):
    confirmation_token: str = Field(..., description='Short-lived confirmation token from delete-request endpoint')
