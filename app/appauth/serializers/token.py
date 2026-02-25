# appauth/api.py
from ninja import Schema


class ExchangeIn(Schema):
    google_id_token: str


class ExchangeOut(Schema):
    access_token: str
    refresh_token: str


class RefreshIn(Schema):
    refresh_token: str
