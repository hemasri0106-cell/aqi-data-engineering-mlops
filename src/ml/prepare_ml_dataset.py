import os
import pandas as pd
import numpy as np
import logging
from sqlalchemy import text
from src.database.connection import get_engine

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ML_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'ml')

def load_data_from_db():
    engine = get_engine()
    query = """
    SELECT 
        d.station_id,
        s.city,
        d.date,
        d.pm25,
        d.no2,
        d.aqi,
        d.aqi_category,
        d.temperature_c,
        d.humidity_pct,
        d.precipitation_mm,
        d.wind_speed_kmh
    FROM daily_aqi d
    JOIN stations s ON d.station_id = s.station_id
    ORDER BY d.station_id, d.date
    """
    df = pd.read_sql_query(query, engine)
    df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)
    return df

def create_features_and_targets(df):
    logger.info("Creating features and targets...")
    # Ensure sorted by station and date
    df = df.sort_values(by=['station_id', 'date']).reset_index(drop=True)
    
    # Target: next day's AQI and Category
    # Since dates might have gaps, we should ideally use shift(-1) if the dates are contiguous,
    # OR merge on date + 1. Since we can have missing days, let's create a target dataframe and merge.
    
    # Time features
    df['day_of_week'] = df['date'].dt.dayofweek
    df['month'] = df['date'].dt.month
    
    result_dfs = []
    
    for station, group in df.groupby('station_id'):
        group = group.copy()
        group = group.sort_values('date')
        # Reindex to fill date gaps with NaNs to make shifts mathematically correct for lags/rolling
        date_range = pd.date_range(start=group['date'].min(), end=group['date'].max(), freq='D')
        group = group.set_index('date').reindex(date_range).rename_axis('date').reset_index()
        group['station_id'] = station
        group['city'] = group['city'].ffill().bfill() # City doesn't change
        
        # TARGETS (Shift -1: Next day's AQI)
        group['target_next_day_aqi'] = group['aqi'].shift(-1)
        group['target_next_day_category'] = group['aqi_category'].shift(-1)
        
        # LAG FEATURES (Shift 1, 2, 3)
        for col in ['aqi', 'pm25', 'no2']:
            group[f'{col}_lag_1'] = group[col].shift(1)
            group[f'{col}_lag_2'] = group[col].shift(2)
            group[f'{col}_lag_3'] = group[col].shift(3)
            
        # ROLLING FEATURES (calculated on PAST data only, so use shift(1) then rolling)
        for col in ['aqi', 'pm25', 'no2']:
            past_series = group[col].shift(1)
            group[f'{col}_roll_mean_3d'] = past_series.rolling(window=3, min_periods=1).mean()
            group[f'{col}_roll_mean_7d'] = past_series.rolling(window=7, min_periods=1).mean()
            group[f'{col}_roll_std_7d'] = past_series.rolling(window=7, min_periods=2).std()
            
        result_dfs.append(group)
        
    final_df = pd.concat(result_dfs, ignore_index=True)
    
    # Drop rows where target is missing (since we can't train/eval on them)
    # Also drop rows where current day AQI is missing, since it's the core feature
    final_df = final_df.dropna(subset=['target_next_day_aqi', 'aqi'])
    
    # We can also drop the artificially created rows during reindexing that don't have current day data
    final_df = final_df.dropna(subset=['pm25'])
    
    return final_df

def split_and_save(df):
    logger.info("Splitting dataset chronologically...")
    # Sort chronologically
    df = df.sort_values('date').reset_index(drop=True)
    
    total_len = len(df)
    train_idx = int(total_len * 0.70)
    val_idx = int(total_len * 0.85)
    
    train_df = df.iloc[:train_idx]
    val_df = df.iloc[train_idx:val_idx]
    test_df = df.iloc[val_idx:]
    
    logger.info(f"Train size: {len(train_df)}")
    logger.info(f"Val size: {len(val_df)}")
    logger.info(f"Test size: {len(test_df)}")
    
    os.makedirs(os.path.join(ML_DATA_DIR, 'features'), exist_ok=True)
    os.makedirs(os.path.join(ML_DATA_DIR, 'train'), exist_ok=True)
    os.makedirs(os.path.join(ML_DATA_DIR, 'validation'), exist_ok=True)
    os.makedirs(os.path.join(ML_DATA_DIR, 'test'), exist_ok=True)
    
    df.to_csv(os.path.join(ML_DATA_DIR, 'features', 'ml_features_full.csv'), index=False)
    train_df.to_csv(os.path.join(ML_DATA_DIR, 'train', 'train.csv'), index=False)
    val_df.to_csv(os.path.join(ML_DATA_DIR, 'validation', 'validation.csv'), index=False)
    test_df.to_csv(os.path.join(ML_DATA_DIR, 'test', 'test.csv'), index=False)
    
    # Validation report
    report = f"""
    ML Dataset Verification Report
    ================================
    Total Historical Period: {df['date'].min().date()} to {df['date'].max().date()}
    Number of Stations: {df['station_id'].nunique()}
    Number of Cities: {df['city'].nunique()}
    Number of ML Rows (after target shifting & dropping missing targets): {len(df)}
    Number of Features: {len(df.columns) - 4}  # Excluding date, station, target cols
    
    Target Statistics (Next Day AQI):
    Mean: {df['target_next_day_aqi'].mean():.2f}
    Min: {df['target_next_day_aqi'].min()}
    Max: {df['target_next_day_aqi'].max()}
    
    Missing Values in Features:
    {df.drop(columns=['target_next_day_aqi', 'target_next_day_category']).isnull().sum().to_string()}
    
    Date Ranges:
    Train: {train_df['date'].min().date()} to {train_df['date'].max().date()} ({len(train_df)} rows)
    Val:   {val_df['date'].min().date()} to {val_df['date'].max().date()} ({len(val_df)} rows)
    Test:  {test_df['date'].min().date()} to {test_df['date'].max().date()} ({len(test_df)} rows)
    
    Leakage Check: Target dates are exactly one day after feature dates (enforced by shift(-1) on contiguous date index).
    """
    logger.info(report)
    with open(os.path.join(ML_DATA_DIR, 'validation_report.txt'), 'w') as f:
        f.write(report)

def main():
    df = load_data_from_db()
    logger.info(f"Loaded {len(df)} raw station-day records from DB.")
    if len(df) == 0:
        logger.error("No data found in DB!")
        return
        
    ml_df = create_features_and_targets(df)
    split_and_save(ml_df)
    
if __name__ == "__main__":
    main()
