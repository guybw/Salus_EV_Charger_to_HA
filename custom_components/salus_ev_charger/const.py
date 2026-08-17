"""Constants for the Salus EV Charger integration."""

DOMAIN = "salus_ev_charger"

USER_POOL_ID = "eu-central-1_XGRz3CgoY"
APP_CLIENT_ID = "4pk5efh3v84g5dav43imsv4fbj"
IDENTITY_POOL_ID = "eu-central-1:60912c00-287d-413b-a2c9-ece3ccef9230"
REGION = "eu-central-1"
IOT_ENDPOINT = "a24u3z7zzwrtdl-ats.iot.eu-central-1.amazonaws.com"
DYNAMODB_TABLE = "UserToDeviceList"

CONF_REFRESH_TOKEN = "refresh_token"
CONF_THING_NAME = "thing_name"

DEFAULT_SCAN_INTERVAL = 30  # seconds
MIN_SCAN_INTERVAL = 30
MAX_SCAN_INTERVAL = 300

# Shadow reported-property paths (nested under state.reported.000000000003.properties)
PROP_PREFIX = "ep0:sCharger:"

# Min/max for the max-charging-current number entity. 6A is the standard
# IEC 61851 minimum; MaxChargingCurrentSupported (32A here) is the ceiling
# but is read dynamically from the shadow rather than hardcoded as the max.
MIN_CHARGING_CURRENT = 6
