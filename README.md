# Salus EV Charger for Home Assistant

A Home Assistant custom integration for the **Salus EVT7UK** 7kW Type 2 tethered EV
charger — live power/energy monitoring, charging status, and remote control
(start/stop, max current, off-peak schedule, connector lock), all without disturbing
the official Salus app or the charger's own connection to Salus's cloud.

> **⚠️ Early release.** This has been running reliably on one charger for about a
> week, but it's new and unofficial. If something doesn't work, or you'd like a
> feature that isn't here yet, please [open an issue](../../issues) — bug reports and
> feature requests are very welcome.

## Is this for you?

This targets the **Salus EVT7UK** (model identifier `SALV7TU01`), sold in the UK as a
7kW/32A single-phase tethered Type 2 charger. It talks to the same cloud backend the
official **Salus EV Charger** app uses, run by a white-label EV charging platform
called **Uleeco** — the same platform also appears to power other rebranded chargers
(a brand called **Vaylen** shows up alongside Salus in some of the charger's own
configuration screens, though it's unconfirmed whether that's a direct sibling
product). If your charger is sold under a different brand but feels similar to this
one, this integration *may* work for you too, unmodified or with minor tweaks. Worth
a try either way — and please report back via an issue if it does or doesn't.

## Why not just use OCPP?

The charger does speak OCPP 1.6 to Salus's cloud, and you *can* point it at your own
OCPP server (e.g. Home Assistant's [`ocpp`](https://github.com/lbbrhzn/ocpp)
integration) instead — full native control, but it permanently disconnects the
charger from Salus, so the official app stops working. This integration instead uses
the same login and cloud API the app itself uses, so **the Salus app keeps working
side by side with Home Assistant**. See [Limitations](#limitations) below for the
one real trade-off that comes with that choice.

## Features

**Sensors:** power, energy, charger current, household current (CT clamp, if fitted),
charging status, availability, error code & info, firmware version, max charging
current supported, load curtailment status, transaction ID, OTA update status.

**Controls:** charging on/off, off-peak schedule on/off, max charging current
(dynamic slider up to your charger's supported maximum), connector lock/unlock.

**Configurable poll interval** — 30–300 seconds, adjustable from the integration's
options page after setup.

## Installation

### HACS (custom repository)

1. HACS → Integrations → ⋮ (top-right menu) → Custom repositories
2. Repository: `https://github.com/guybw/Salus_EV_Charger_to_HA`, category: Integration
3. Install "Salus EV Charger", then restart Home Assistant

### Manual

1. Copy the `custom_components/salus_ev_charger/` folder from this repo into your
   Home Assistant config's `custom_components/` directory
2. Restart Home Assistant

### Setup

Settings → Devices & Services → Add Integration → **Salus EV Charger** → enter the
same email and password you use to log into the Salus EV Charger app.

## How it works (short version)

Logs into AWS Cognito with your Salus account, exchanges that for temporary AWS
credentials, looks up your charger's AWS IoT "thing name", then reads its live state
from an **AWS IoT Device Shadow** — the same data source the app's own dashboard
uses. Controls write to the shadow's `desired` state, which the charger picks up over
its existing OCPP connection to Salus, exactly like tapping a button in the app does.
Nothing about the charger's configuration or its connection to Salus is touched. Only
a Cognito **refresh token** is stored (in Home Assistant's encrypted config entry
storage) — never your password.

## Limitations

- **No temperature data, and voltage isn't currently working.** Voltage was observed
  briefly reporting real values while directly testing the charger's connection
  during an active charging session, so it's known to be *possible* — it's just not
  wired up to a working data source in this integration yet. Tracked as an open bug,
  see [issues](../../issues). Temperature hasn't been found from any accessible data
  source so far — tracked as an open question, also in [issues](../../issues).
- **Cloud-dependent.** This polls Salus's AWS backend, not the charger directly on
  your LAN. Requires internet access to function.
- A couple of the write-control formats (charging on/off, connector lock) were
  inferred by analogy with confirmed ones rather than directly observed — they've
  worked reliably in a week of testing, but flagging it for transparency.

## Contributing / Issues

This is a first release scoped to what one person's charger and testing could cover.
If you hit a bug, want a feature (more entities, faster local access if that ever
becomes possible, support for a different charger model on the same platform), please
[open an issue](../../issues) — reports from other charger models/regions are
especially useful for figuring out how much of this generalizes.

## Disclaimer

Unofficial, community-built integration. Not affiliated with, endorsed by, or
supported by Salus Controls or Uleeco. Uses the same account login and backend API
the official app uses — no vulnerabilities are exploited, but this is an unofficial
integration built around an undocumented API, which could change or break without
notice.

## License

[GPL-3.0](LICENSE)

## Also known as / search terms

If you found this by searching for any of the following, you're in the right place:
Salus EVT7UK Home Assistant, Salus EV Charger Home Assistant integration, Salus
EVT7UK Home Assistant integration, SalusConnect EV charger Home Assistant, Salus
smart EV charger Home Assistant, Salus 7kW EV charger Home Assistant, Salus Type 2
tethered EV charger Home Assistant, Uleeco EV charger Home Assistant, Vaylen EV
charger Home Assistant, HACS Salus EV charger, HACS EV charger integration, Home
Assistant wallbox integration UK, Salus EVT7UK API, Salus EVT7UK custom component,
EV charger AWS Cognito Home Assistant, EV charger AWS IoT Home Assistant Device
Shadow.
