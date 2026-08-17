"""API client for the Salus EV Charger cloud backend.

Talks to the same AWS Cognito / DynamoDB / AWS IoT Device Shadow backend the
official Salus app uses. This is a synchronous class -- callers in async
Home Assistant code must invoke its methods via
`hass.async_add_executor_job(...)`.
"""
from __future__ import annotations

import json
from typing import Any

import boto3
from pycognito import Cognito

from .const import (
    APP_CLIENT_ID,
    DYNAMODB_TABLE,
    IDENTITY_POOL_ID,
    IOT_ENDPOINT,
    REGION,
    USER_POOL_ID,
)


class SalusApiError(Exception):
    """Raised when the Salus/AWS backend can't be reached or returns an error."""


def extract_reported_properties(shadow: dict[str, Any]) -> dict[str, Any]:
    """Pull the flat ep0:sCharger:* property dict out of a raw shadow document."""
    try:
        reported = shadow["state"]["reported"]
        component = reported["000000000003"]
        return component.get("properties", {})
    except (KeyError, TypeError):
        return {}


class SalusApiClient:
    """Wraps Cognito auth, AWS credential exchange, DynamoDB lookup and IoT shadow access."""

    def __init__(self, username: str, refresh_token: str | None = None, thing_name: str | None = None) -> None:
        self.username = username
        self._refresh_token = refresh_token
        self._thing_name = thing_name
        self._cognito: Cognito | None = None
        self._identity_id: str | None = None
        self._aws_creds: dict[str, Any] | None = None
        self._aws_creds_expiry: float = 0

    @property
    def refresh_token(self) -> str | None:
        """Current refresh token, to persist in the config entry."""
        return self._refresh_token

    def login(self, password: str) -> None:
        """Initial SRP login with a password. Only used during config flow setup."""
        cognito = Cognito(USER_POOL_ID, APP_CLIENT_ID, username=self.username)
        try:
            cognito.authenticate(password=password)
        except Exception as exc:  # noqa: BLE001 -- surface any Cognito failure uniformly
            raise SalusApiError(f"Login failed: {exc}") from exc
        self._cognito = cognito
        self._refresh_token = cognito.refresh_token

    def _ensure_cognito(self) -> Cognito:
        if self._cognito is None:
            if not self._refresh_token:
                raise SalusApiError("No refresh token available; login() must be called first")
            self._cognito = Cognito(
                USER_POOL_ID,
                APP_CLIENT_ID,
                username=self.username,
                refresh_token=self._refresh_token,
            )
            # A freshly-constructed Cognito object has no access_token yet --
            # check_token() requires one to already exist (it only checks
            # expiry), so the very first fetch must go through
            # renew_access_token() directly instead.
            try:
                self._cognito.renew_access_token()
            except Exception as exc:  # noqa: BLE001
                raise SalusApiError(f"Initial token fetch failed: {exc}") from exc
        else:
            try:
                self._cognito.check_token()
            except Exception as exc:  # noqa: BLE001
                raise SalusApiError(f"Token refresh failed: {exc}") from exc
        if self._cognito.refresh_token:
            self._refresh_token = self._cognito.refresh_token
        return self._cognito

    def _ensure_aws_credentials(self) -> dict[str, Any]:
        import time

        if self._aws_creds and time.time() < self._aws_creds_expiry:
            return self._aws_creds

        cognito = self._ensure_cognito()
        identity_client = boto3.client("cognito-identity", region_name=REGION)
        login_provider = f"cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}"

        try:
            identity = identity_client.get_id(
                IdentityPoolId=IDENTITY_POOL_ID,
                Logins={login_provider: cognito.id_token},
            )
            self._identity_id = identity["IdentityId"]
            creds = identity_client.get_credentials_for_identity(
                IdentityId=self._identity_id,
                Logins={login_provider: cognito.id_token},
            )
        except Exception as exc:  # noqa: BLE001
            raise SalusApiError(f"AWS credential exchange failed: {exc}") from exc

        self._aws_creds = creds["Credentials"]
        # Refresh a minute early to avoid edge-of-expiry failures.
        self._aws_creds_expiry = self._aws_creds["Expiration"].timestamp() - 60
        return self._aws_creds

    def _iot_client(self):
        creds = self._ensure_aws_credentials()
        return boto3.client(
            "iot-data",
            region_name=REGION,
            endpoint_url=f"https://{IOT_ENDPOINT}",
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretKey"],
            aws_session_token=creds["SessionToken"],
        )

    def _dynamodb_client(self):
        creds = self._ensure_aws_credentials()
        return boto3.client(
            "dynamodb",
            region_name=REGION,
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretKey"],
            aws_session_token=creds["SessionToken"],
        )

    def get_thing_name(self) -> str:
        """Look up (and cache) the AWS IoT thing name for this account's charger."""
        if self._thing_name:
            return self._thing_name

        self._ensure_aws_credentials()  # populates self._identity_id
        dynamodb = self._dynamodb_client()
        try:
            resp = dynamodb.query(
                TableName=DYNAMODB_TABLE,
                KeyConditionExpression="userid = :v",
                ExpressionAttributeValues={":v": {"S": self._identity_id}},
            )
        except Exception as exc:  # noqa: BLE001
            raise SalusApiError(f"DynamoDB device lookup failed: {exc}") from exc

        items = resp.get("Items", [])
        if not items:
            raise SalusApiError("No devices found for this Salus account")
        own = json.loads(items[0]["Own"]["S"])
        device_list = own.get("list", [])
        if not device_list:
            raise SalusApiError("Account has no owned devices")
        self._thing_name = device_list[0]
        return self._thing_name

    def get_shadow(self) -> dict[str, Any]:
        """Fetch the charger's current AWS IoT device shadow."""
        thing_name = self.get_thing_name()
        iot = self._iot_client()
        try:
            response = iot.get_thing_shadow(thingName=thing_name)
        except Exception as exc:  # noqa: BLE001
            raise SalusApiError(f"Shadow fetch failed: {exc}") from exc
        return json.loads(response["payload"].read())

    # Observed in the live shadow: reported/desired properties sit nested
    # under state.<x>.000000000003.properties, not flat at the top level.
    SHADOW_COMPONENT_ID = "000000000003"

    def update_shadow(self, properties: dict[str, Any]) -> None:
        """Write to the shadow's desired state, e.g. {'ep0:sCharger:SetChargingOn': 1}."""
        thing_name = self.get_thing_name()
        iot = self._iot_client()
        payload = json.dumps(
            {
                "state": {
                    "desired": {
                        self.SHADOW_COMPONENT_ID: {"properties": properties},
                    }
                }
            }
        ).encode()
        try:
            iot.update_thing_shadow(thingName=thing_name, payload=payload)
        except Exception as exc:  # noqa: BLE001
            raise SalusApiError(f"Shadow update failed: {exc}") from exc
