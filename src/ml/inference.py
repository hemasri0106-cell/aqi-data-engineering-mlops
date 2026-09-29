import pandas as pd
import requests
import json
import logging
from sqlalchemy import text
from src.database.connection import get_engine

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

API_URL = "http://localhost:8000"

def get_latest_features_for_station(station_id: int):
    """
    Fetches the latest historical data for a station and computes
    all 29 ML features required by the model.
    """
    engine = get_engine()
    
    # We need at least 8 days of data to compute 7-day rolling metrics and 3-day lags
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
    WHERE d.station_id = :station_id
    ORDER BY d.date DESC
    LIMIT 10
    """
    
    with engine.connect() as conn:
        df = pd.read_sql_query(text(query), conn, params={"station_id": station_id})
        
    if df.empty:
        return None, "No data available for this station."
        
    # Sort chronologically
    df = df.sort_values('date').reset_index(drop=True)
    df['date'] = pd.to_datetime(df['date'])
    
    # Time features
    df['day_of_week'] = df['date'].dt.dayofweek
    df['month'] = df['date'].dt.month
    
    # Fill date gaps with NaNs to make shifts mathematically correct
    date_range = pd.date_range(start=df['date'].min(), end=df['date'].max(), freq='D')
    df = df.set_index('date').reindex(date_range).rename_axis('date').reset_index()
    
    # Forward fill static/semi-static cols if needed
    df['station_id'] = station_id
    df['city'] = df['city'].ffill().bfill()
    
    # Lags (Shift 1, 2, 3)
    for col in ['aqi', 'pm25', 'no2']:
        df[f'{col}_lag_1'] = df[col].shift(1)
        df[f'{col}_lag_2'] = df[col].shift(2)
        df[f'{col}_lag_3'] = df[col].shift(3)
        
    # Rolling (Shift 1 then roll)
    for col in ['aqi', 'pm25', 'no2']:
        past_series = df[col].shift(1)
        df[f'{col}_roll_mean_3d'] = past_series.rolling(window=3, min_periods=1).mean()
        df[f'{col}_roll_mean_7d'] = past_series.rolling(window=7, min_periods=1).mean()
        df[f'{col}_roll_std_7d'] = past_series.rolling(window=7, min_periods=2).std()
        
    # Get the LAST row (the latest date)
    latest_row = df.iloc[-1]
    
    # Check if the latest row actually has data (not just a NaN row from reindex gap at the end)
    if pd.isna(latest_row['aqi']):
        return None, "Latest date has missing AQI data, cannot predict next day."
        
    # Build payload
    payload = latest_row.drop('date').to_dict()
    
    # Replace NaNs with None for JSON serialization
    for k, v in payload.items():
        if pd.isna(v):
            payload[k] = None
            
    prediction_date = (latest_row['date'] + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    latest_data_date = latest_row['date'].strftime("%Y-%m-%d")
            
    return {
        "payload": payload,
        "prediction_date": prediction_date,
        "latest_data_date": latest_data_date
    }, None

def predict_next_day(station_id: int):
    data, error = get_latest_features_for_station(station_id)
    if error:
        return {"error": error}
        
    payload = data["payload"]
    
    try:
        reg_resp = requests.post(f"{API_URL}/predict/regression", json=payload, timeout=5)
        clf_resp = requests.post(f"{API_URL}/predict/classification", json=payload, timeout=5)
        
        if reg_resp.status_code == 200 and clf_resp.status_code == 200:
            return {
                "success": True,
                "prediction_date": data["prediction_date"],
                "latest_data_date": data["latest_data_date"],
                "predicted_aqi": reg_resp.json().get("predicted_aqi"),
                "predicted_category": clf_resp.json().get("predicted_category"),
                "reg_model_version": reg_resp.json().get("model_version"),
                "clf_model_version": clf_resp.json().get("model_version"),
            }
        else:
            return {"error": f"API Error: Reg: {reg_resp.status_code}, Clf: {clf_resp.status_code}"}
    except Exception as e:
        return {"error": f"Connection Error: {str(e)}"}
