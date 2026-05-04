# InfluxDB: Connection, Schema, and Queries (Home Assistant)

This document captures the verified details of your InfluxDB setup, how to connect to it, and practical query patterns tailored to Home Assistant (HA) metrics with a focus on Climate & Air Quality.

## Environment Verified

- InfluxDB host: `http://YOUR_INFLUXDB_IP:8086`
- Version: InfluxDB 1.8.10 (from `GET /ping` → `X-Influxdb-Version: 1.8.10`)
- Database: `home_assistant`
- Measurements observed in `home_assistant`:
  - Unit-based: `"°C"`, `"%"`, `"hPa"`, `"ppm"`, `"ppb"`, `"µg/m³"`, `"μg/m³"`
  - Generic: `"state"` (numeric values for some entities without a unit)
  - Others present: `% available`, `A`, `CAD`, `COP`, `EUR`, `L`, `L/min`, `MiB`, `V`, `W`, `alerts`, `dBm`, `floors`, `hour`, `kB`, `kWh`, `km`, `m`, `m/s`, `mA`, `mAh`, `min`, `m³`, `pulses`, `steps`, `㎡`

Note on micro symbols in measurements:
- Both `"µg/m³"` (U+00B5 MICRO SIGN) and `"μg/m³"` (U+03BC GREEK MU) exist. Queries must use the exact measurement name that holds your data.

## Authentication and Permissions

Observed issue: `{"error":"authorization failed"}` when running `SELECT` queries as user `homeassistant`.

You need a user with at least READ privileges on the `home_assistant` database. From an admin-capable InfluxDB client (or `influx` shell):

```sql
-- Grant read to existing user
GRANT READ ON "home_assistant" TO "homeassistant";

-- Alternatively, create a dedicated read-only user for Grafana
CREATE USER "grafana_ro" WITH PASSWORD 'change-me-strong';
GRANT READ ON "home_assistant" TO "grafana_ro";
```

Tips
- `SHOW GRANTS FOR <user>` requires admin privilege; if you lack admin, simply test a `SELECT` from a measurement to confirm access.
- If your password contains special characters (e.g., `#`), ensure it is properly quoted in Grafana and CLI commands.

## Connectivity Checks (CLI)

Ping and version:
```bash
curl -sSI http://YOUR_INFLUXDB_IP:8086/ping
```

List databases (InfluxDB 1.x):
```bash
curl -sS --get 'http://YOUR_INFLUXDB_IP:8086/query' \
  --data-urlencode 'q=SHOW DATABASES' \
  -u homeassistant:'your-password'
```

List measurements in `home_assistant`:
```bash
curl -sS --get 'http://YOUR_INFLUXDB_IP:8086/query' \
  --data-urlencode 'db=home_assistant' \
  --data-urlencode 'q=SHOW MEASUREMENTS' \
  -u homeassistant:'your-password'
```

List retention policies (optional):
```bash
curl -sS --get 'http://YOUR_INFLUXDB_IP:8086/query' \
  --data-urlencode 'q=SHOW RETENTION POLICIES ON "home_assistant"' \
  -u homeassistant:'your-password'
```

## Home Assistant Schema Primer

With HA’s default InfluxDB integration configuration, numeric sensors are usually written to a measurement named by their unit (`unit_as_measurement: true`), field `value`, tag `entity_id`. Some entities without a unit are written to measurement `state` with numeric `value`.

Common patterns we’ve validated on your instance:
- Temperature → measurement `"°C"`, field `value`, tag `entity_id`
- Humidity → `"%"`
- Pressure → `"hPa"`
- eCO2 → `"ppm"`
- TVOC → `"ppb"`
- Particulates → `"µg/m³"` or `"μg/m³"`
- AQI and some fan speeds → `"state"` (numeric)

If your HA integration uses a different schema (e.g., all metrics under `state` with a `unit_of_measurement` tag), adapt queries accordingly (see below).

## Example InfluxQL Queries (Unit-as-Measurement)

Last value examples:
```sql
-- Indoor desktop temperature
SELECT last("value") FROM "°C" WHERE ("entity_id"='sensor.espdesktop_ath_temperature');

-- Bathroom humidity
SELECT last("value") FROM "%" WHERE ("entity_id"='sensor.bathroom_sensor_humidity');

-- Pressure
SELECT last("value") FROM "hPa" WHERE ("entity_id"='sensor.espdesktop_bmp_pressure');

-- eCO2 / TVOC
SELECT last("value") FROM "ppm" WHERE ("entity_id"='sensor.espdesktop_ens160_eco2');
SELECT last("value") FROM "ppb" WHERE ("entity_id"='sensor.espdesktop_ens160_total_volatile_organic_compounds');

-- AQI (numeric state)
SELECT last("value") FROM "state" WHERE ("entity_id"='sensor.espdesktop_ens160_air_quality_index');

-- PM2.5 (try both measurement names if needed)
SELECT last("value") FROM "µg/m³" WHERE ("entity_id"='sensor.espdesktop_pm_2_5_m');
SELECT last("value") FROM "μg/m³" WHERE ("entity_id"='sensor.espdesktop_pm_2_5_m');
```

Time-series with aggregation (for Grafana panels):
```sql
-- Average over $__interval
SELECT mean("value") FROM "°C"
  WHERE ("entity_id"='sensor.exterior_temp_hum_temperature') AND $timeFilter
  GROUP BY time($__interval) fill(null);
```

## Example InfluxQL Queries (All-in-`state` schema)

If your HA integration does NOT use unit-as-measurement, use `state` with `unit_of_measurement` tag filters:
```sql
-- Temperature in °C
SELECT mean("value") FROM "state"
  WHERE ("entity_id"='sensor.espdesktop_ath_temperature' AND "unit_of_measurement"='°C') AND $timeFilter
  GROUP BY time($__interval) fill(null);

-- Humidity in %
SELECT mean("value") FROM "state"
  WHERE ("entity_id"='sensor.bathroom_sensor_humidity' AND "unit_of_measurement"='%') AND $timeFilter
  GROUP BY time($__interval) fill(null);

-- PM2.5 in µg/m³
SELECT mean("value") FROM "state"
  WHERE ("entity_id"='sensor.espdesktop_pm_2_5_m' AND ("unit_of_measurement"='µg/m³' OR "unit_of_measurement"='μg/m³')) AND $timeFilter
  GROUP BY time($__interval) fill(null);
```

## Grafana Datasource Configuration (InfluxDB 1.8)

- Type: `InfluxDB`
- Query Language: `InfluxQL`
- URL: `http://YOUR_INFLUXDB_IP:8086`
- Database: `home_assistant`
- Auth: `User` and `Password` (read-only recommended)
- Min time interval: `10s` or `30s` (optional)

Permissions
- Ensure the configured Grafana user has `READ` on `home_assistant`.
- For production, prefer a dedicated read-only user (easier to rotate and audit).

## Common Pitfalls & Troubleshooting

- Authorization failed: grant `READ` on the database to the user used by Grafana.
- No data in panels:
  - Verify time range (try Last 7 days).
  - Confirm measurement names (especially micro symbol variants for particulates).
  - Check that your datasource uses InfluxQL (not Flux) for InfluxDB 1.8.
  - Validate an entity by running a `SELECT last("value")` query in Grafana Explore.
- Special characters: When using CLI or provisioning, quote measurement names: `"%"`, `"°C"`, `"µg/m³"`.
- Retention policy: If you use a non-default RP, prefix measurement with RP (e.g., `"autogen"."°C"`).

## Related Dashboards

- Grafana (Home Assistant datasource): `graphana/climate_air_quality.json`
- Grafana (InfluxDB InfluxQL): `graphana/climate_air_quality_influxdb.json`

These dashboards assume the measurement-per-unit schema shown above. If your data is all under `state`, adapt panels to the `state` patterns provided in this document.

