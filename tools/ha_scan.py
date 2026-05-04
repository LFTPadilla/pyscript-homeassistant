import os
import json
import urllib.request


KEYWORDS = [
    "temperature",
    "humidity",
    "pm25",
    "pm_2_5",
    "pm2_5",
    "pm2.5",
    "particulate",
    "air_quality",
    "aqi",
    "co2",
    "carbon_dioxide",
    "voc",
    "tvoc",
    "pressure",
    "dew_point",
    "dewpoint",
    "pm1",
    "pm10",
]

DEVICE_CLASSES = {
    "temperature",
    "humidity",
    "pm25",
    "pm1",
    "pm10",
    "carbon_dioxide",
    "aqi",
    "volatile_organic_compounds",
    "volatile_organic_compounds_parts",
    "pressure",
    "dew_point",
}


def fetch_states():
    base = os.environ.get("HA_URL", "").rstrip("/")
    token = os.environ.get("HA_TOKEN")
    if not base or not token:
        raise SystemExit("Missing HA_URL or HA_TOKEN in environment")
    url = f"{base}/api/states"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)


def relevant(s):
    eid = s.get("entity_id", "")
    domain = eid.split(".")[0] if "." in eid else ""
    attrs = s.get("attributes", {})
    dc = (attrs.get("device_class") or "").lower()
    fn = (attrs.get("friendly_name") or "").lower()

    if domain in ("climate", "fan"):
        return True
    if domain == "switch" and ("air_purifier" in eid or "purifier" in fn):
        return True
    if domain == "sensor":
        low = eid.lower()
        if any(k in low for k in KEYWORDS):
            return True
        if dc in DEVICE_CLASSES:
            return True
    return False


def main():
    data = fetch_states()
    rows = []
    for s in data:
        if not relevant(s):
            continue
        eid = s.get("entity_id", "")
        domain = eid.split(".")[0]
        attrs = s.get("attributes", {})
        rows.append(
            {
                "entity_id": eid,
                "domain": domain,
                "device_class": (attrs.get("device_class") or "").lower() or None,
                "unit": attrs.get("unit_of_measurement"),
                "state_class": attrs.get("state_class"),
                "friendly_name": attrs.get("friendly_name"),
            }
        )

    rows.sort(key=lambda x: (x["domain"], x["entity_id"]))
    for k in rows:
        eid = k["entity_id"].ljust(40)
        dc = (k["device_class"] or "-").ljust(18)
        unit = (k["unit"] or "-").ljust(8)
        sc = (k["state_class"] or "-").ljust(10)
        fn = k["friendly_name"] or ""
        print(f"{eid} | dc={dc} | unit={unit} | sc={sc} | {fn}")


if __name__ == "__main__":
    main()

