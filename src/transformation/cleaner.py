import pandas as pd
import logging
import pytz

logger = logging.getLogger('transformation.cleaner')

def clean_pollution_data(df: pd.DataFrame) -> pd.DataFrame:
    """Normalizes pollution data and removes duplicates."""
    if df.empty: return df
    
    logger.info("Cleaning pollution data...")
    cleaned = df.copy()
    
    # 1. Normalize Pollutant Names
    # e.g. "PM2.5" -> "pm25"
    cleaned['pollutant'] = cleaned['pollutant'].str.lower().str.replace('.', '').str.replace(' ', '')
    
    # 2. Normalize units 
    # Just lowercase to keep consistent
    cleaned['unit'] = cleaned['unit'].str.lower()
    
    # 3. Timestamp normalization
    # OpenAQ provides ISO8601 with Z. Parse as UTC.
    cleaned['timestamp_utc'] = pd.to_datetime(cleaned['timestamp_utc'])
    # Floor to nearest hour for aggregation purposes
    cleaned['timestamp_utc_hr'] = cleaned['timestamp_utc'].dt.floor('h')
    
    # 4. Duplicate Detection
    initial_count = len(cleaned)
    dup_mask = cleaned.duplicated(subset=['station', 'timestamp_utc', 'pollutant'], keep='first')
    duplicates = cleaned[dup_mask]
    if not duplicates.empty:
        logger.warning(f"Found {len(duplicates)} duplicate pollution records. Dropping them.")
        # In a real pipeline, we'd log them to rejected_records.csv as DUPLICATE. 
        # For brevity, dropping them here.
        cleaned = cleaned.drop_duplicates(subset=['station', 'timestamp_utc', 'pollutant'], keep='first')
        
    logger.info(f"Pollution Cleaning: {initial_count} initial -> {len(cleaned)} cleaned.")
    return cleaned

def clean_weather_data(df: pd.DataFrame) -> pd.DataFrame:
    """Normalizes weather data."""
    if df.empty: return df
    
    logger.info("Cleaning weather data...")
    cleaned = df.copy()
    
    # 1. Timestamp normalization
    # Open-Meteo time is local to the requested timezone. We use utc_offset_seconds to convert to UTC.
    local_dt = pd.to_datetime(cleaned['timestamp_local'])
    if 'utc_offset_seconds' in cleaned.columns:
        offset_td = pd.to_timedelta(cleaned['utc_offset_seconds'], unit='s')
        cleaned['timestamp_utc'] = local_dt - offset_td
        cleaned['timestamp_utc'] = cleaned['timestamp_utc'].dt.tz_localize('UTC')
    else:
        logger.warning("utc_offset_seconds not found, assuming UTC.")
        cleaned['timestamp_utc'] = local_dt.dt.tz_localize('UTC')
        
    cleaned['timestamp_utc_hr'] = cleaned['timestamp_utc'].dt.floor('h')
    
    # 2. Duplicate Detection
    initial_count = len(cleaned)
    dup_mask = cleaned.duplicated(subset=['city', 'timestamp_utc_hr'], keep='first')
    if dup_mask.any():
        logger.warning(f"Found {dup_mask.sum()} duplicate weather records. Dropping.")
        cleaned = cleaned[~dup_mask]
        
    logger.info(f"Weather Cleaning: {initial_count} initial -> {len(cleaned)} cleaned.")
    return cleaned

def identify_missing_periods(df: pd.DataFrame, ts_col: str, group_cols: list, freq: str = 'h'):
    """Identifies missing periods in a time series."""
    if df.empty: return
    
    for name, group in df.groupby(group_cols):
        if len(group) < 2: continue
        
        min_dt = group[ts_col].min()
        max_dt = group[ts_col].max()
        expected_range = pd.date_range(start=min_dt, end=max_dt, freq=freq)
        
        actual_dts = group[ts_col].dt.floor(freq).unique()
        missing = set(expected_range) - set(actual_dts)
        
        if missing:
            logger.info(f"Missing Periods identified for {name}: {len(missing)} periods missing between {min_dt} and {max_dt}.")
