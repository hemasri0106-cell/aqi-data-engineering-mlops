# AQI Methodology

This project calculates the Air Quality Index (AQI) based on the **Indian National Air Quality Index (NAQI)** standard, as implemented in `src/transformation/aggregator.py`.

## Pollutants Monitored
The calculation relies on the 24-hour moving averages (calculated via daily rollup in this project) of the following criteria pollutants:
- **PM2.5** (Fine Particulate Matter)
- **NO2** (Nitrogen Dioxide)

*(While the NAQI standard also encompasses PM10, SO2, CO, and O3, this project focuses specifically on PM2.5 and NO2 based on API availability and project scope).*

## Breakpoints & Sub-Indices
The sub-index for each pollutant is calculated using piecewise linear interpolation against the Indian NAQI breakpoints:

**PM2.5 Breakpoints (µg/m³):**
- Good (0-50): 0 to 30
- Satisfactory (51-100): 31 to 60
- Moderate (101-200): 61 to 90
- Poor (201-300): 91 to 120
- Very Poor (301-400): 121 to 250
- Severe (401-500): 251 to 1000

**NO2 Breakpoints (µg/m³):**
- Good (0-50): 0 to 40
- Satisfactory (51-100): 41 to 80
- Moderate (101-200): 81 to 180
- Poor (201-300): 181 to 280
- Very Poor (301-400): 281 to 400
- Severe (401-500): 401 to 1000

## Calculation Logic
1. **Rounding**: The daily average concentration for a pollutant is first rounded to the nearest integer.
2. **Linear Interpolation**: The sub-index is calculated using the standard formula:
   `I = ((I_high - I_low) / (C_high - C_low)) * (C - C_low) + I_low`
   where `C` is the concentration, `C_low`/`C_high` are the concentration breakpoints, and `I_low`/`I_high` are the AQI breakpoints.
3. **Missing Pollutants**: If a pollutant is missing for a given day, its sub-index evaluates to `NaN`.

## Final Station AQI
The final AQI for a specific station on a given day is the **maximum** of its available sub-indices:
`Station AQI = MAX(Sub-Index(PM2.5), Sub-Index(NO2))`

## City AQI Methodology (Critical Distinction)
**City AQI is NOT calculated by averaging the AQI values of individual stations.**

Mathematically, averaging index values skews the non-linear health impact scale. Instead, the project uses the following methodology for the analytical layer (`daily_city_aqi`):
1. **Spatial Aggregation**: The raw pollutant concentrations (PM2.5, NO2) are averaged across all available stations within the city for that day.
2. **Index Application**: The NAQI formula is then applied *dynamically* to these spatially averaged concentrations to compute the City-level sub-indices.
3. **City AQI**: The final City AQI is the maximum of the newly calculated City sub-indices.

## Category Mapping
The final numerical AQI is mapped to a descriptive health category:
- `0 - 50`: **Good**
- `51 - 100`: **Satisfactory**
- `101 - 200`: **Moderate**
- `201 - 300`: **Poor**
- `301 - 400`: **Very Poor**
- `> 400`: **Severe**
- `NaN`: **Unknown** (Insufficient Data)
