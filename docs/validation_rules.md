# Validation Rules

The Air Quality pipeline enforces several layers of data validation during Phase 3 (Transformation) and Phase 4 (PostgreSQL Loading) to ensure analytical data integrity. These rules are explicitly implemented in `src/pipeline_phase3.py` and `src/database/models.py`.

## 1. Timestamp Normalization
- **Rule**: All inbound OpenAQ measurements (which may have varied offsets) are parsed, localized, and converted to UTC using `pd.to_datetime(..., utc=True)`.
- **Reason**: Ensures temporal alignment between disparate stations and APIs.
- **Rule**: Hourly granularity is enforced by flooring timestamps to the start of the hour using `.dt.floor('h')`.

## 2. Uniqueness and Duplication Checks
- **Hourly Uniqueness**: Duplicate readings for the same pollutant, at the same station, in the same hour, are resolved by grouping and taking the `mean()` across duplicate measurements.
- **Database Constraints**: The PostgreSQL schema physically rejects duplicate fact observations using `UNIQUE` constraints.
  - `hourly_air_quality`: `UNIQUE (station_id, timestamp_utc)`
  - `daily_aqi`: `UNIQUE (station_id, date)`
  - `daily_city_aqi`: `UNIQUE (city, date)`
- **Idempotent Loading**: The loading scripts use `INSERT ... ON CONFLICT DO UPDATE` (upsert mechanics) against these constraints to ensure identical pipeline runs don't create duplicate database records.

## 3. Pollutant Validation
- **Missing Timestamps**: Any raw JSON record lacking a valid timestamp or value is strictly dropped and routed to the rejected records queue.
- **Range Checks**: 
  - PM2.5 and NO2 values less than `0.0` are flagged as anomalous. 
  - These failed records are removed from the analytical path and appended to `data/rejected/rejected_records.csv` alongside the rejection reason (e.g., `"Negative pollution value"`).

## 4. Weather Validation
- Weather is treated as contextual enrichment data.
- **Join Rule**: A `LEFT JOIN` is used when merging pollution (left) and weather (right). Weather data that does not correspond to an existing pollution observation is discarded.
- If a station has pollution data but weather data is missing (e.g., API failure), the pipeline proceeds. Weather parameters simply remain `NULL` (or `NaN` in pandas), ensuring that pollution facts are never artificially dropped due to missing meteorological context.

## 5. Missing-Period Detection
- After floor-rounding to the hour, the pipeline generates a continuous hourly date range between the earliest and latest observation for each station.
- It compares the existing timestamps against this continuous expected index to identify missing intervals.
- The pipeline *logs* the number of missing periods for monitoring but does *not* artificially fabricate or backfill missing pollution data.

## 6. Rejected Record Handling
- Invalid records (failed date parsing, negative concentrations, missing mandatory keys) are not silently dropped.
- They are transformed into an error schema `{'original_data': ..., 'rejection_reason': ..., 'timestamp': ...}` and appended to `data/rejected/rejected_records.csv` for downstream auditing.

## 7. AQI Validation & Fallbacks
- The Indian National Air Quality Index (NAQI) requires specific sub-indices.
- If a required pollutant parameter (like PM2.5 or NO2) is `NaN` because the sensor was offline, the sub-index for that specific pollutant evaluates to `NaN`.
- The final AQI evaluates to the maximum valid sub-index. If *no* valid sub-indices exist for the station on that day, the AQI is left as `NaN`, and the category falls back to `"Unknown"`. 
- No default or imputed values are inserted into the analytical layer.
