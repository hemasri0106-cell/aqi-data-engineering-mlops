from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Station(Base):
    __tablename__ = 'stations'
    
    station_id = Column(Integer, primary_key=True, autoincrement=True)
    station_name = Column(String, nullable=False)
    city = Column(String, nullable=False)
    source = Column(String)
    location_id = Column(Integer, unique=True, nullable=False)
    latitude = Column(Float)
    longitude = Column(Float)

class HourlyAirQuality(Base):
    __tablename__ = 'hourly_air_quality'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    station_id = Column(Integer, ForeignKey('stations.station_id'), nullable=False)
    timestamp_utc = Column(DateTime(timezone=True), nullable=False)
    
    no2 = Column(Float)
    pm25 = Column(Float)
    temperature_c = Column(Float)
    humidity_pct = Column(Float)
    precipitation_mm = Column(Float)
    wind_speed_kmh = Column(Float)
    
    __table_args__ = (
        UniqueConstraint('station_id', 'timestamp_utc', name='uq_hourly_station_time'),
        Index('idx_hourly_station_id', 'station_id'),
        Index('idx_hourly_timestamp', 'timestamp_utc'),
        Index('idx_hourly_station_time', 'station_id', 'timestamp_utc')
    )

class DailyAQI(Base):
    __tablename__ = 'daily_aqi'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    station_id = Column(Integer, ForeignKey('stations.station_id'), nullable=False)
    date = Column(Date, nullable=False)
    
    no2 = Column(Float)
    pm25 = Column(Float)
    temperature_c = Column(Float)
    humidity_pct = Column(Float)
    precipitation_mm = Column(Float)
    wind_speed_kmh = Column(Float)
    
    aqi_pm25 = Column(Float)
    aqi_no2 = Column(Float)
    aqi = Column(Float)
    aqi_category = Column(String)
    
    __table_args__ = (
        UniqueConstraint('station_id', 'date', name='uq_daily_station_date'),
        Index('idx_daily_station_id', 'station_id'),
        Index('idx_daily_date', 'date')
    )

class DailyCityAQI(Base):
    __tablename__ = 'daily_city_aqi'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    city = Column(String, nullable=False)
    date = Column(Date, nullable=False)
    
    no2 = Column(Float)
    pm25 = Column(Float)
    temperature_c = Column(Float)
    humidity_pct = Column(Float)
    precipitation_mm = Column(Float)
    wind_speed_kmh = Column(Float)
    
    aqi_pm25 = Column(Float)
    aqi_no2 = Column(Float)
    aqi = Column(Float)
    aqi_category = Column(String)
    
    __table_args__ = (
        UniqueConstraint('city', 'date', name='uq_daily_city_date'),
        Index('idx_city_daily_city', 'city'),
        Index('idx_city_daily_date', 'date')
    )
