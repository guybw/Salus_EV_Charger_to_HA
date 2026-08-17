"""Shared helpers for reading values out of the flat shadow properties dict."""
from __future__ import annotations

from typing import Any

CONNECTOR = "connector_1"


def flat(properties: dict[str, Any], key: str) -> Any:
    """Read a device-level (non-connector-scoped) property."""
    return properties.get(key)


def connector(properties: dict[str, Any], key: str) -> Any:
    """Read a per-connector property, unwrapping the connector_1 nesting."""
    val = properties.get(key)
    if isinstance(val, dict):
        return val.get(CONNECTOR)
    return val


def meter(properties: dict[str, Any], field: str) -> Any:
    """Read a field out of the nested MeterValues.connector_1 object."""
    values = properties.get("ep0:sCharger:MeterValues")
    if isinstance(values, dict):
        conn = values.get(CONNECTOR)
        if isinstance(conn, dict):
            return conn.get(field)
    return None
