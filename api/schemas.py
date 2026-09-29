from pydantic import BaseModel, Field
from typing import Optional

class PredictionRequest(BaseModel):
    station_id: int
    city: str
    pm25: float
    no2: float
    aqi: float
    aqi_category: str
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    precipitation_mm: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    day_of_week: float
    month: float
    aqi_lag_1: Optional[float] = None
    aqi_lag_2: Optional[float] = None
    aqi_lag_3: Optional[float] = None
    pm25_lag_1: Optional[float] = None
    pm25_lag_2: Optional[float] = None
    pm25_lag_3: Optional[float] = None
    no2_lag_1: Optional[float] = None
    no2_lag_2: Optional[float] = None
    no2_lag_3: Optional[float] = None
    aqi_roll_mean_3d: Optional[float] = None
    aqi_roll_mean_7d: Optional[float] = None
    aqi_roll_std_7d: Optional[float] = None
    pm25_roll_mean_3d: Optional[float] = None
    pm25_roll_mean_7d: Optional[float] = None
    pm25_roll_std_7d: Optional[float] = None
    no2_roll_mean_3d: Optional[float] = None
    no2_roll_mean_7d: Optional[float] = None
    no2_roll_std_7d: Optional[float] = None

class RegressionResponse(BaseModel):
    prediction_type: str = "next_day_aqi"
    predicted_aqi: float
    model_name: str = "AQI_Next_Day_AQI_Regression"
    model_version: str

class ClassificationResponse(BaseModel):
    prediction_type: str = "next_day_category"
    predicted_category: str
    model_name: str = "AQI_Next_Day_Category_Classification"
    model_version: str
