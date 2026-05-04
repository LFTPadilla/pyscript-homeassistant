Grafana Dashboards

This folder contains ready-to-import Grafana dashboards focused on Climate & Air Quality for the Home Assistant entities discovered in your environment.

How to use
- Import the JSON dashboard in Grafana: Dashboards → New → Import → Upload JSON.
- When prompted, select your Home Assistant datasource (via the Grafana Home Assistant datasource plugin) or map the placeholder input to your datasource.
- Adjust panel queries if your datasource or plugin differs.

Assumptions
- Uses the Grafana Home Assistant datasource plugin (preferred). If you use InfluxDB/Prometheus instead, adapt queries accordingly.
- Entity IDs are based on what was detected (e.g., `sensor.bathroom_sensor_temperature`, `sensor.espdesktop_ens160_pm_2_5_m`, etc.). Update panels if your names differ.

Files
- `climate_air_quality.json` — Comprehensive dashboard for temperature, humidity, pressure, AQI, eCO2, TVOC, PM1/2.5/10, and humidity vs fan speed correlation.
- `climate_air_quality_influxdb.json` — Same dashboard, but using the InfluxDB datasource with InfluxQL queries following Home Assistant’s default Influx schema (measurements per unit like `"°C"`, `"%"`, `"hPa"`, `"ppm"`, `"ppb"`, `"µg/m³"`, and `"state"`).

Notes for InfluxDB users
- This assumes the default Home Assistant InfluxDB integration schema:
  - Numeric sensors with a unit are written to a measurement named by the unit (`"°C"`, `"%"`, `"ppm"`, etc.), field `value`, tag `entity_id`.
  - Sensors without a unit (e.g., AQI, some fan speeds) are written to `"state"` as numeric `value` when possible.
- If your schema differs (custom `override_measurement`, etc.), update the measurement names or WHERE filters in each panel query.

Create a solid dashboard (Influx best practices)
- Datasource: use `InfluxDB` with Query Language `InfluxQL` (InfluxDB 1.8). Set Database to `home_assistant` and a user with READ permission. See INFLUX.md.
- Entity tag: in WHERE clauses, do NOT include the domain prefix. Example: `WHERE ("entity_id"='t_h_sensor_temperature')` not `sensor.t_h_sensor_temperature`.
- Measurements: use the unit-as-measurement names HA writes:
  - Temperature `"°C"`, Humidity `"%"`, Pressure `"hPa"`, eCO2 `"ppm"`, TVOC `"ppb"`.
  - Particulates can exist as `"µg/m³"` or `"μg/m³"`. Use a regex measurement: `FROM /^(µ|μ)g\/m³$/`.
  - For unitless numeric sensors (AQI, some fan speeds), use measurement `"state"`.
- Queries:
  - Time series: `SELECT mean("value") ... AND $timeFilter GROUP BY time($__interval) fill(null)`.
  - Single value: `SELECT last("value") ... AND $timeFilter` (often no group by).
  - Combine axes when comparing different scales (e.g., humidity vs fan speed) and set per-series units in panel Field overrides.
- Aliases: keep them short and readable (e.g., “Bathroom”, “Kitchen”, “PM2.5”, “AQI”).
- Units and thresholds:
  - RH: percent with soft thresholds at 60/70.
  - PM2.5: µg/m³ with 12/35/55 thresholds.
  - AQI: color steps around 50/100/150 as needed.
- Validation workflow:
  1) Explore → run `SHOW MEASUREMENTS` to confirm names.
  2) Test a single entity: `SELECT last("value") FROM "°C" WHERE ("entity_id"='t_h_sensor_temperature')`.
  3) If no rows, verify permissions and the exact `entity_id` tag value (no domain).
- Performance:
  - Set dashboard Min interval to `10s`–`30s`.
  - Prefer mean over raw values at dashboard scale; drill down with shorter time ranges for detail.

Tip: INFLUX.md contains complete schema notes, example queries, and permission commands.
